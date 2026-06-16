import asyncio
import time
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading

from engine import AnalysisEngine
from bmd45_loader import BMD45Loader
from backend_logs import backend_logs

@dataclass
class LaneState:
    id: int
    image_path: str
    image_url: str
    density: float
    vehicle_counts: Dict[str, int]
    green_time: int
    light_status: str = "RED"
    remaining_time: int = 0
    detections: List[Dict] = field(default_factory=list)
    has_passed: bool = False
    next_image_path: Optional[str] = None
    next_result: Optional[Dict] = None

@dataclass
class SessionState:
    session_id: str
    lanes: int
    max_green_time: int
    lane_data: List[LaneState]
    current_green_lane: int = -1
    last_update: float = 0.0
    phase_start_time: float = 0.0
    is_active: bool = True
    cycle_count: int = 0
    cycle_queue: List[int] = field(default_factory=list)
    speed_multiplier: int = 1

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        self.lock = threading.Lock()
        self.engine = AnalysisEngine()
        self.bmd45 = BMD45Loader()
        # Start background refresh loop
        self._start_refresh_loop()

    def _sort_queue(self, session: SessionState):
        """Sort cycle queue based on current densities without downloading new images."""
        indexed_densities = [(i, lane.density) for i, lane in enumerate(session.lane_data)]
        indexed_densities.sort(key=lambda x: x[1], reverse=True)
        session.cycle_queue = [x[0] for x in indexed_densities]
        
        # Reset has_passed for all lanes when a new cycle starts
        for lane in session.lane_data:
            lane.has_passed = False
             
        print(f"[SessionManager] New cycle queue sorted by density: {session.cycle_queue}")
        backend_logs.add(
            "INFO",
            "SessionManager",
            "New signal cycle queue sorted by density",
            details={"session_id": session.session_id, "cycle_queue": [idx + 1 for idx in session.cycle_queue]},
        )

    def create_session(self, lanes: int, max_green_time: int) -> SessionState:
        """Create a new session, download images, and run initial analysis."""
        session_id = str(uuid.uuid4())[:8]
        print(f"[SessionManager] Creating session {session_id} with {lanes} lanes")
        backend_logs.add(
            "INFO",
            "SessionManager",
            f"Creating session {session_id}",
            details={"session_id": session_id, "lanes": lanes, "max_green_time": max_green_time},
        )

        # Download N images for initial state
        image_paths = self.bmd45.download_images(lanes)

        # Initialize and analyze lanes
        lane_data = []
        for i in range(lanes):
            lane_data.append(LaneState(
                id=i + 1,
                image_path="",
                image_url="",
                density=0.0,
                vehicle_counts={"motor": 0, "car": 0, "heavy": 0},
                green_time=0,
                light_status="RED",
            ))

        for i, img_path in enumerate(image_paths):
            lane = lane_data[i]
            if img_path:
                result = self.engine.analyze_image(img_path, max_green_time)
                lane.image_path = img_path
                lane.image_url = result["image_url"]
                lane.density = result["density"]
                lane.vehicle_counts = result["vehicle_counts"]
                lane.green_time = result["green_time"]
                lane.detections = result["detections"]

        current_time = time.time()
        session = SessionState(
            session_id=session_id,
            lanes=lanes,
            max_green_time=max_green_time,
            lane_data=lane_data,
            current_green_lane=-1,
            last_update=current_time,
            phase_start_time=current_time,
            is_active=True,
            cycle_count=0,
            cycle_queue=[]
        )

        # Sort initially
        self._sort_queue(session)
        
        # Pop first lane
        green_lane = session.cycle_queue.pop(0)
        session.lane_data[green_lane].light_status = "GREEN"
        session.lane_data[green_lane].remaining_time = session.lane_data[green_lane].green_time
        
        session.current_green_lane = green_lane
        session.phase_start_time = current_time

        # Add to sessions dict only after it's fully initialized
        with self.lock:
            self.sessions[session_id] = session
            
        print(f"[SessionManager] Session {session_id} created. Initial green lane: {green_lane + 1}")
        backend_logs.add(
            "INFO",
            "SessionManager",
            f"Session {session_id} created",
            details={"session_id": session_id, "initial_green_lane": green_lane + 1},
        )
        
        # Start pre-fetching for the first green lane
        threading.Thread(target=self._prefetch_or_update, args=(session, green_lane), daemon=True).start()
        
        return session

    def stop_session(self, session_id: str):
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                print(f"[SessionManager] Session {session_id} stopped and removed.")
                backend_logs.add(
                    "INFO",
                    "SessionManager",
                    f"Session {session_id} stopped and removed",
                    details={"session_id": session_id},
                )

    def get_session(self, session_id: str) -> Optional[SessionState]:
        with self.lock:
            return self.sessions.get(session_id)

    def update_speed(self, session_id: str, speed: int) -> Optional[SessionState]:
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                current_time = time.time()
                # Calculate old elapsed time so we can adjust phase_start_time without jumping
                old_elapsed = (current_time - session.phase_start_time) * session.speed_multiplier
                session.speed_multiplier = speed
                # Shift start time back to match the new speed curve
                session.phase_start_time = current_time - (old_elapsed / speed)
            return session

    def update_max_green_time(self, session_id: str, max_green_time: int) -> Optional[SessionState]:
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.max_green_time = max_green_time
                # Recalculate green times for all lanes
                for lane in session.lane_data:
                    lane.green_time = self.engine.density.calculate_green_time(lane.density, max_green_time)
                # If green lane is active, update its remaining time proportionally
                if session.current_green_lane >= 0:
                    green_lane = session.lane_data[session.current_green_lane]
                    if green_lane.light_status == "GREEN":
                        green_lane.remaining_time = green_lane.green_time
            return session

    def _prefetch_or_update(self, session: SessionState, lane_idx: int):
        """Fetch the next image for a lane while it is green. If it finishes after the turn, update directly."""
        try:
            new_image_path = self.bmd45.get_one_image()
            if new_image_path:
                result = self.engine.analyze_image(new_image_path, session.max_green_time)
                with self.lock:
                    if lane_idx >= 0 and lane_idx < len(session.lane_data):
                        lane = session.lane_data[lane_idx]
                        if lane.light_status == "GREEN":
                            # Still green, store for instant swap later
                            lane.next_result = result
                            lane.next_image_path = new_image_path
                        else:
                            # Already finished its turn! Update immediately so frontend sees it.
                            lane.image_path = new_image_path
                            lane.image_url = result["image_url"]
                            lane.density = result["density"]
                            lane.vehicle_counts = result["vehicle_counts"]
                            lane.green_time = result["green_time"]
                            lane.detections = result["detections"]
        except Exception as e:
            print(f"[SessionManager] Pre-fetch error: {e}")
            backend_logs.add(
                "ERROR",
                "SessionManager",
                "Pre-fetch failed",
                details={"session_id": session.session_id, "lane": lane_idx + 1},
                exc=e,
            )

    def _swap_green_lane(self, session: SessionState):
        """Instantly swap green lane and apply pre-fetched images."""
        with self.lock:
            green_idx = session.current_green_lane

            if green_idx >= 0 and green_idx < len(session.lane_data):
                lane = session.lane_data[green_idx]
                lane.has_passed = True
                if lane.next_result:
                    lane.image_path = lane.next_image_path
                    lane.image_url = lane.next_result["image_url"]
                    lane.density = lane.next_result["density"]
                    lane.vehicle_counts = lane.next_result["vehicle_counts"]
                    lane.green_time = lane.next_result["green_time"]
                    lane.detections = lane.next_result["detections"]
                    lane.next_result = None
                    lane.next_image_path = None

            # Reset all to RED
            for lane in session.lane_data:
                lane.light_status = "RED"
                lane.remaining_time = 0

            # Advance queue
            if not session.cycle_queue:
                self._sort_queue(session)
                session.cycle_count += 1

            if session.cycle_queue:
                new_green = session.cycle_queue.pop(0)
            else:
                new_green = 0 # Fallback

            # Set new green lane
            session.lane_data[new_green].light_status = "GREEN"
            session.lane_data[new_green].remaining_time = session.lane_data[new_green].green_time
            session.current_green_lane = new_green
            session.phase_start_time = time.time()
            session.last_update = time.time()

        print(f"[SessionManager] Session {session.session_id} cycled. New green: {new_green + 1}")
        backend_logs.add(
            "INFO",
            "SessionManager",
            f"Session {session.session_id} cycled to lane {new_green + 1}",
            details={"session_id": session.session_id, "new_green_lane": new_green + 1},
        )
        
        # Start pre-fetching for the NEW green lane
        threading.Thread(target=self._prefetch_or_update, args=(session, new_green), daemon=True).start()

    def _update_timers(self):
        while True:
            try:
                current_time = time.time()
                sessions_to_refresh = []
                with self.lock:
                    for session in list(self.sessions.values()):
                        if not session.is_active:
                            continue
                            
                        if session.current_green_lane >= 0:
                            green_lane = session.lane_data[session.current_green_lane]
                            elapsed = (current_time - session.phase_start_time) * session.speed_multiplier
                            remaining = max(0, green_lane.green_time - int(elapsed))
                            green_lane.remaining_time = remaining
                            
                            if remaining <= 0:
                                sessions_to_refresh.append(session)
                                
                # Process light swapping INSTANTLY outside the loop
                for session in sessions_to_refresh:
                    try:
                        self._swap_green_lane(session)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        print(f"[SessionManager] ERROR in _swap_green_lane: {e}")
                        backend_logs.add(
                            "ERROR",
                            "SessionManager",
                            "Failed to swap green lane",
                            details={"session_id": session.session_id},
                            exc=e,
                        )
                    # No finally block needed since is_active is no longer set to False!
                        
            except Exception as e:
                import traceback
                traceback.print_exc()
            time.sleep(1)

    def _start_refresh_loop(self):
        """Start a background thread that updates timers every second."""
        def loop():
            self._update_timers()

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        print("[SessionManager] Background refresh loop started")
        backend_logs.add("INFO", "SessionManager", "Background refresh loop started")

    def to_dict(self, session: SessionState) -> Dict:
        """Convert session state to JSON-serializable dict."""
        return {
            "session_id": session.session_id,
            "lanes": session.lanes,
            "max_green_time": session.max_green_time,
            "cycle_count": session.cycle_count,
            "current_green_lane": session.current_green_lane + 1 if session.current_green_lane >= 0 else 0,
            "lanes_data": [
                {
                    "id": lane.id,
                    "image_url": lane.image_url,
                    "density": lane.density,
                    "vehicle_counts": lane.vehicle_counts,
                    "light_status": lane.light_status,
                    "green_time": lane.green_time,
                    "remaining_time": lane.remaining_time,
                    "has_passed": lane.has_passed,
                }
                for lane in session.lane_data
            ],
            "last_update": session.last_update,
            "speed_multiplier": session.speed_multiplier,
        }

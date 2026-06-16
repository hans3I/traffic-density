from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import socket
import threading
import traceback
import uuid
from typing import Any, Deque, Dict, List, Optional


@dataclass
class BackendLogEntry:
    id: str
    timestamp: str
    level: str
    source: str
    message: str
    trace_id: str
    server_host: str
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class BackendLogStore:
    def __init__(self, max_entries: int = 2000):
        self.max_entries = max_entries
        self.entries: Deque[BackendLogEntry] = deque(maxlen=max_entries)
        self.lock = threading.Lock()
        self.server_host = socket.gethostname()

    def add(
        self,
        level: str,
        source: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        exc: Optional[BaseException] = None,
    ) -> BackendLogEntry:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entry = BackendLogEntry(
            id=f"log_{uuid.uuid4().hex[:10]}",
            timestamp=timestamp,
            level=level.upper(),
            source=source,
            message=message,
            trace_id=f"trc_{uuid.uuid4().hex[:16]}",
            server_host=self.server_host,
            details=details,
            stack_trace="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else None,
        )

        with self.lock:
            self.entries.appendleft(entry)
        return entry

    def list(
        self,
        level: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
        since_hours: Optional[int] = 24,
    ) -> Dict[str, Any]:
        limit = max(1, min(limit, self.max_entries))
        level_filter = level.upper() if level else None
        source_filter = source.lower() if source else None
        search_filter = search.lower() if search else None
        since = None

        if since_hours and since_hours > 0:
            since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

        with self.lock:
            snapshot = list(self.entries)

        filtered: List[BackendLogEntry] = []
        sources = set()
        levels = set()

        for entry in snapshot:
            levels.add(entry.level)
            sources.add(entry.source)

            if level_filter and entry.level != level_filter:
                continue
            if source_filter and entry.source.lower() != source_filter:
                continue
            if since:
                entry_time = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
                if entry_time < since:
                    continue
            if search_filter:
                haystack = " ".join(
                    [
                        entry.id,
                        entry.level,
                        entry.source,
                        entry.message,
                        entry.trace_id,
                        entry.server_host,
                        str(entry.details or ""),
                    ]
                ).lower()
                if search_filter not in haystack:
                    continue

            filtered.append(entry)

        return {
            "logs": [asdict(entry) for entry in filtered[:limit]],
            "total": len(snapshot),
            "filtered_total": len(filtered),
            "sources": sorted(sources),
            "levels": sorted(levels),
        }


backend_logs = BackendLogStore()

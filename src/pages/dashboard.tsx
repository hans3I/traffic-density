import { useState, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import DashboardGrid from '@/components/DashBoard';
import TrafficCard, { LaneData } from '@/components/TrafficCard';

interface BackendLane {
  id: number;
  image_url: string;
  density: number;
  vehicle_counts: {
    motor: number;
    auto: number;
    car: number;
    heavy: number;
  };
  light_status: 'OFF' | 'RED' | 'GREEN';
  green_time: number;
  remaining_time: number;
  has_passed: boolean;
}

interface BackendState {
  session_id: string;
  lanes: number;
  max_green_time: number;
  cycle_count: number;
  current_green_lane: number;
  lanes_data: BackendLane[];
  last_update: number;
  speed_multiplier: number;
}

interface StoredSession {
  sessionId: string;
}

const ACTIVE_SESSION_STORAGE_KEY = 'trafficai.activeSession';
const POLL_INTERVAL_MS = 4000;

async function readErrorMessage(response: Response) {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    const data = await response.json();
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.message === 'string') return data.message;
  }

  const text = await response.text();
  return text || 'Terjadi kesalahan saat menghubungi backend.';
}

function mapBackendLanes(lanesData: BackendLane[]): LaneData[] {
  return lanesData.map((lane) => ({
    id: lane.id,
    imageUrl: lane.image_url || null,
    density: lane.density,
    vehicleCounts: lane.vehicle_counts,
    lightStatus: lane.light_status,
    greenTime: lane.green_time,
    remainingTime: lane.remaining_time,
    hasPassed: lane.has_passed,
  }));
}

function saveActiveSession(sessionId: string) {
  if (typeof window === 'undefined') return;
  const payload: StoredSession = { sessionId };
  window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, JSON.stringify(payload));
  window.dispatchEvent(new Event('trafficai-session-change'));
}

function clearActiveSession() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
  window.dispatchEvent(new Event('trafficai-session-change'));
}

function readActiveSession() {
  if (typeof window === 'undefined') return null;

  try {
    const rawSession = window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
    if (!rawSession) return null;

    const parsedSession = JSON.parse(rawSession) as StoredSession;
    return parsedSession.sessionId ? parsedSession : null;
  } catch {
    clearActiveSession();
    return null;
  }
}

export default function DashboardPage() {
  const [laneCount, setLaneCount] = useState<number>(4);
  const [lanes, setLanes] = useState<LaneData[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [maxGreenTime, setMaxGreenTime] = useState<number>(60);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [cycleCount, setCycleCount] = useState<number>(0);
  const [speed, setSpeed] = useState<number>(1);
  const [isRestoringSession, setIsRestoringSession] = useState<boolean>(true);

  const applyBackendState = (state: BackendState) => {
    setLanes(mapBackendLanes(state.lanes_data));
    setLaneCount(state.lanes);
    setMaxGreenTime(state.max_green_time);
    setSessionId(state.session_id);
    setIsAnalyzing(true);
    setCycleCount(state.cycle_count);
    setSpeed(state.speed_multiplier || 1);
    setError(null);
    saveActiveSession(state.session_id);
  };

  const resetAnalysisState = (nextError?: string | null) => {
    setIsAnalyzing(false);
    setSessionId(null);
    setCycleCount(0);
    setSpeed(1);
    clearActiveSession();
    setError(nextError ?? null);
    setLanes((prev) =>
      prev.map((lane) => ({
        ...lane,
        imageUrl: null,
        density: 0,
        vehicleCounts: { motor: 0, auto: 0, car: 0, heavy: 0 },
        lightStatus: 'OFF',
        greenTime: 0,
        remainingTime: 0,
        hasPassed: false,
      }))
    );
  };

  useEffect(() => {
    const storedSession = readActiveSession();

    if (!storedSession) {
      setIsRestoringSession(false);
      return;
    }

    const restoreSession = async () => {
      try {
        const response = await fetch(`/api/traffic?session_id=${storedSession.sessionId}`);
        if (!response.ok) {
          clearActiveSession();
          setError('Sesi sebelumnya sudah berakhir atau tidak lagi tersedia.');
          return;
        }

        const state: BackendState = await response.json();
        applyBackendState(state);
      } catch (err) {
        console.error('Failed to restore active session:', err);
        setError('Gagal memulihkan sesi analisis yang sedang berjalan. Pastikan backend Python masih aktif.');
      } finally {
        setIsRestoringSession(false);
      }
    };

    restoreSession();
  }, []);

  // Initialize empty lanes when laneCount changes (before analysis)
  useEffect(() => {
    if (!isAnalyzing && !isRestoringSession) {
      setLanes((prevLanes) => {
        if (laneCount > prevLanes.length) {
          const addedLanesCount = laneCount - prevLanes.length;
          const newLanes: LaneData[] = Array.from({ length: addedLanesCount }, (_, i) => ({
            id: prevLanes.length + i + 1,
            imageUrl: null,
            density: 0,
            vehicleCounts: { motor: 0, auto: 0, car: 0, heavy: 0 },
            lightStatus: 'OFF',
            greenTime: 0,
            hasPassed: false,
          }));
          return [...prevLanes, ...newLanes];
        }
        return prevLanes.slice(0, laneCount);
      });
    }
  }, [laneCount, isAnalyzing, isRestoringSession]);

  // Polling: fetch state from backend every 2 seconds
  useEffect(() => {
    if (!sessionId || !isAnalyzing) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/traffic?session_id=${sessionId}`);
        if (!response.ok) {
          if (response.status === 404) {
            resetAnalysisState('Sesi analisis sudah berakhir karena idle atau melewati batas waktu.');
            return;
          }

          console.warn('Polling failed or skipped');
          return;
        }
        
        const state: BackendState = await response.json();
        applyBackendState(state);
      } catch (err) {
        console.error('Polling error:', err);
        // Don't show error immediately on polling, might be temporary
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(pollInterval);
  }, [sessionId, isAnalyzing]);

  const incrementLanes = () => {
    if (laneCount < 4) {
      setLaneCount((prev) => prev + 1);
    }
  };

  const decrementLanes = () => {
    if (laneCount > 1) {
      setLaneCount((prev) => prev - 1);
    }
  };

  const incrementMaxGreenTime = () => {
    if (maxGreenTime < 60) {
      setMaxGreenTime((prev) => prev + 1);
    }
  };

  const decrementMaxGreenTime = () => {
    if (maxGreenTime > 10) {
      setMaxGreenTime((prev) => prev - 1);
    }
  };

  const handleAnalyzeTraffic = async () => {
    if (lanes.length === 0) return;
    setIsLoading(true);
    setError(null);

    try {
      // Call backend to start analysis
      const response = await fetch('/api/traffic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lanes: laneCount,
          max_green_time: maxGreenTime,
        }),
      });
      
      if (!response.ok) {
        const errorText = await readErrorMessage(response);
        throw new Error(errorText || 'Koneksi ke server AI terputus');
      }
      
      const state: BackendState = await response.json();
      applyBackendState(state);
    } catch (error: any) {
      console.error('Error analyzing traffic:', error);
      setError('Gagal melakukan analisis AI. Pastikan backend Python sudah berjalan.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopAnalysis = async () => {
    if (sessionId) {
      try {
        await fetch(`/api/traffic?session_id=${sessionId}`, { method: 'DELETE' });
      } catch (err) {
        console.error("Failed to stop session:", err);
      }
    }

    resetAnalysisState(null);
  };

  const cycleSpeed = async () => {
    if (!sessionId || !isAnalyzing) return;
    
    // Cycle logic: 1 -> 2 -> 3 -> 5 -> 1
    const nextSpeed = speed === 1 ? 2 : speed === 2 ? 3 : speed === 3 ? 5 : 1;
    
    try {
      const response = await fetch('/api/speed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          speed: nextSpeed,
        }),
      });
      if (response.ok) {
        const state: BackendState = await response.json();
        applyBackendState(state);
      }
    } catch (e) {
      console.error("Failed to change speed");
    }
  };

  return (
    <div className="bg-background text-on-background font-body-md min-h-screen flex antialiased">
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar isAnalyzing={isAnalyzing} activePage="dashboard" />

        <main className="flex-1 p-container-padding overflow-y-auto">
          <section className="bg-surface-container-high/40 backdrop-blur-xl border border-outline-variant/30 rounded-xl p-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-6 shadow-lg">
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex flex-col gap-2">
                <label className="font-label-mono text-[12px] text-on-surface-variant uppercase tracking-wider">Ruas Jalan</label>
                <div className="flex items-center bg-surface-container-lowest border border-outline-variant/50 rounded-lg overflow-hidden focus-within:border-primary transition-colors">
                  <button
                    type="button"
                    onClick={decrementLanes}
                    disabled={laneCount <= 1 || isAnalyzing}
                    className="p-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-on-surface-variant"
                    aria-label="Kurangi ruas jalan"
                  >
                    <span className="material-symbols-outlined text-[18px]">remove</span>
                  </button>
                  <span className="w-16 text-center bg-transparent border-none text-on-surface font-headline-md text-headline-md select-none">
                    {laneCount}
                  </span>
                  <button
                    type="button"
                    onClick={incrementLanes}
                    disabled={laneCount >= 4 || isAnalyzing}
                    className="p-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-on-surface-variant"
                    aria-label="Tambah ruas jalan"
                  >
                    <span className="material-symbols-outlined text-[18px]">add</span>
                  </button>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="font-label-mono text-[12px] text-on-surface-variant uppercase tracking-wider">Max Waktu Hijau</label>
                <div className="flex items-center bg-surface-container-lowest border border-outline-variant/50 rounded-lg overflow-hidden focus-within:border-primary transition-colors">
                  <button
                    type="button"
                    onClick={decrementMaxGreenTime}
                    disabled={maxGreenTime <= 10 || isAnalyzing}
                    className="p-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-on-surface-variant"
                    aria-label="Kurangi waktu hijau maksimum"
                  >
                    <span className="material-symbols-outlined text-[18px]">remove</span>
                  </button>
                  <span className="w-20 text-center bg-transparent border-none text-on-surface font-headline-md text-headline-md select-none">
                    {maxGreenTime}
                  </span>
                  <button
                    type="button"
                    onClick={incrementMaxGreenTime}
                    disabled={maxGreenTime >= 60 || isAnalyzing}
                    className="p-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-on-surface-variant"
                    aria-label="Tambah waktu hijau maksimum"
                  >
                    <span className="material-symbols-outlined text-[18px]">add</span>
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 w-full md:w-auto mt-4 md:mt-0">
              <button
                type="button"
                onClick={cycleSpeed}
                disabled={!isAnalyzing}
                className="hidden sm:flex px-4 py-2 bg-surface-container-lowest border border-outline-variant/50 rounded-lg items-center gap-2 transition-colors disabled:opacity-50 enabled:hover:border-primary"
              >
                <span className="font-label-mono text-[12px] text-on-surface-variant">{speed}x Speed</span>
                <span className="material-symbols-outlined text-[16px] text-on-surface-variant">speed</span>
              </button>

              {!isAnalyzing ? (
                <button
                  type="button"
                  onClick={handleAnalyzeTraffic}
                  disabled={isLoading || isRestoringSession}
                  className={`flex-1 md:flex-none text-on-primary-container font-headline-md text-sm px-8 py-4 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 font-bold tracking-wide ${
                    isLoading || isRestoringSession
                      ? 'bg-primary-container/70 cursor-not-allowed animate-pulse'
                      : 'bg-primary-container hover:bg-primary'
                  }`}
                >
                  {isRestoringSession ? 'Memulihkan Sesi...' : isLoading ? 'AI Sedang Menghitung...' : 'Mulai Analisis AI'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStopAnalysis}
                  className="flex-1 md:flex-none bg-error hover:bg-red-700 text-on-error font-headline-md text-sm px-8 py-4 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 font-bold tracking-wide"
                >
                  Hentikan Analisis
                </button>
              )}
            </div>
          </section>

          {error && (
            <div className="mb-8 bg-error-container border border-error/25 text-on-error-container p-4 rounded-xl text-sm">
              {error}
            </div>
          )}

          {isAnalyzing && (
            <div className="mb-8 flex items-center justify-between gap-4 text-xs text-on-surface-variant">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                <span>Analisis AI aktif - polling setiap 4 detik</span>
              </div>
              {cycleCount > 0 && <span className="font-label-mono">Siklus #{cycleCount}</span>}
            </div>
          )}

          <DashboardGrid>
            {lanes.map((lane) => (
              <TrafficCard key={lane.id} data={lane} speed={speed} />
            ))}
          </DashboardGrid>
        </main>
      </div>
    </div>
  );
}

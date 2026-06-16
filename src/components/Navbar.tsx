import Link from 'next/link';
import { useEffect, useState } from 'react';

interface NavbarProps {
  isAnalyzing?: boolean;
  activePage?: 'home' | 'dashboard' | 'logs';
}

const navItems = [
  { key: 'home', href: '/', label: 'Home' },
  { key: 'dashboard', href: '/dashboard', label: 'Dashboard' },
  { key: 'logs', href: '/logs', label: 'Backend Logs' },
] as const;

const ACTIVE_SESSION_STORAGE_KEY = 'trafficai.activeSession';

function readActiveSessionId() {
  if (typeof window === 'undefined') return null;

  try {
    const rawSession = window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
    if (!rawSession) return null;

    const parsedSession = JSON.parse(rawSession) as { sessionId?: string };
    return parsedSession.sessionId || null;
  } catch {
    window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    return null;
  }
}

export default function Navbar({ isAnalyzing, activePage = 'home' }: NavbarProps) {
  const [hasActiveSession, setHasActiveSession] = useState(false);
  const showLiveStatus = isAnalyzing ?? hasActiveSession;

  useEffect(() => {
    let isMounted = true;

    const refreshSessionStatus = async () => {
      const sessionId = readActiveSessionId();
      if (!sessionId) {
        if (isMounted) setHasActiveSession(false);
        return;
      }

      try {
        const response = await fetch(`/api/traffic?session_id=${sessionId}`);
        if (!response.ok) {
          window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
          if (isMounted) setHasActiveSession(false);
          return;
        }

        if (isMounted) setHasActiveSession(true);
      } catch {
        if (isMounted) setHasActiveSession(true);
      }
    };

    refreshSessionStatus();
    const interval = window.setInterval(refreshSessionStatus, 5000);
    const handleStorage = () => refreshSessionStatus();

    window.addEventListener('storage', handleStorage);
    window.addEventListener('trafficai-session-change', handleStorage);

    return () => {
      isMounted = false;
      window.clearInterval(interval);
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener('trafficai-session-change', handleStorage);
    };
  }, []);

  return (
    <header className="bg-surface border-b border-outline-variant z-10">
      <div className="flex justify-between items-center w-full px-container-padding py-4 max-w-full">
        <div className="md:hidden flex items-center gap-2">
          <span className="font-headline-md text-headline-md font-bold text-on-surface">
            Traffic<span className="text-primary">AI</span>
          </span>
        </div>

        <nav className="hidden md:flex items-center gap-8 ml-8">
          {navItems.map((item) => (
            <Link
              key={item.key}
              className={
                activePage === item.key
                  ? 'text-primary border-b-2 border-primary pb-1 font-body-md text-body-md font-semibold'
                  : 'text-on-surface-variant hover:text-primary transition-colors duration-200 font-body-md text-body-md'
              }
              href={item.href}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4 ml-auto">
          <div className="hidden sm:flex items-center gap-2 bg-surface-container-low px-3 py-1.5 rounded-full border border-outline-variant/50">
            <span className={`w-2 h-2 rounded-full ${showLiveStatus ? 'bg-primary-container animate-pulse' : 'bg-outline-variant'}`} />
            <span className="font-label-mono text-[12px] text-primary">
              {showLiveStatus ? 'Live Status' : 'Idle Status'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

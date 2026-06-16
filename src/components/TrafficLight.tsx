import { useEffect, useState } from 'react';

interface TrafficLightProps {
  status: 'OFF' | 'RED' | 'GREEN';
  recommendedTime: number;
  remainingTime?: number;
  speedMultiplier?: number;
}

export default function TrafficLight({ status, recommendedTime, remainingTime, speedMultiplier = 1 }: TrafficLightProps) {
  const [displayTime, setDisplayTime] = useState<number>(remainingTime ?? recommendedTime);

  // Update display time when props change from polling
  useEffect(() => {
    if (status !== 'GREEN') {
      setDisplayTime(remainingTime ?? recommendedTime);
    } else {
      // Saat lampu HIJAU, biarkan timer lokal yang bekerja.
      // Kita hanya mengambil waktu dari backend jika selisihnya terlalu jauh (> 3 detik)
      // untuk mencegah efek "ngeblink/patah" karena keterlambatan jaringan.
      setDisplayTime((prev) => {
        const nextTime = remainingTime ?? recommendedTime;
        if (Math.abs(prev - nextTime) > 3) {
          return nextTime;
        }
        return prev;
      });
    }
  }, [remainingTime, recommendedTime, status]);

  // Countdown timer for green light
  useEffect(() => {
    if (status === 'GREEN' && displayTime > 0) {
      const interval = setInterval(() => {
        setDisplayTime((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000 / speedMultiplier); // Dynamically adjust countdown speed

      return () => clearInterval(interval);
    }
  }, [status, displayTime, speedMultiplier]);

  return (
    <div className="bg-surface-container-lowest p-4 flex justify-between items-center border-t border-outline-variant/20">
      <div className="flex gap-4">
        <div 
          className={`w-3 h-3 rounded-full transition-all duration-300 ${
            status === 'RED' 
              ? 'bg-error shadow-[0_0_12px_rgba(186,26,26,0.55)]' 
              : 'bg-surface-variant'
          }`} 
        />

        <div 
          className={`w-3 h-3 rounded-full transition-all duration-300 ${
            status === 'GREEN' 
              ? 'bg-primary shadow-[0_0_12px_rgba(0,100,116,0.55)]' 
              : 'bg-surface-variant'
          }`} 
        />
      </div>

      <div className="flex items-center gap-3">
        <span className="font-label-mono text-[10px] text-on-surface-variant uppercase tracking-widest">Sisa Waktu:</span>
        <span className="font-label-mono text-primary text-sm min-w-8 text-right">
          {status === 'GREEN' && displayTime > 0 ? displayTime : '--'}
        </span>
      </div>
    </div>
  );
}

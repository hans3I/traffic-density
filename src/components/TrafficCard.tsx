import TrafficLight from './TrafficLight';

export interface LaneData {
  id: number;
  imageUrl: string | null;
  density: number;
  vehicleCounts: {
    motor: number;
    auto: number;
    car: number;
    heavy: number;
  };
  lightStatus: 'OFF' | 'RED' | 'GREEN';
  greenTime: number;
  remainingTime?: number;
  hasPassed?: boolean;
}

interface TrafficCardProps {
  data: LaneData;
  speed?: number;
}

export default function TrafficCard({ data, speed = 1 }: TrafficCardProps) {
  const getDensityColor = (density: number) => {
    if (density === 0) return 'bg-surface-container-highest text-on-surface border-outline-variant/30';
    if (density < 40) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (density < 75) return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-red-50 text-red-700 border-red-200';
  };

  const getDensityLabel = (density: number) => {
    if (density === 0) return 'Belum Diketahui';
    if (density < 40) return 'Rendah';
    if (density < 75) return 'Sedang';
    return 'Tinggi';
  };

  const densityLabel = data.density === 0
    ? 'Belum Diketahui'
    : `${data.density.toFixed(1)}% (${getDensityLabel(data.density)})`;

  const vehicleStats = [
    { label: 'Motor', value: data.vehicleCounts.motor },
    { label: 'Auto', value: data.vehicleCounts.auto },
    { label: 'Mobil', value: data.vehicleCounts.car },
    { label: 'Heavy', value: data.vehicleCounts.heavy },
  ];

  return (
    <div className="bg-surface-container-low/60 backdrop-blur-md border border-outline-variant/20 rounded-xl overflow-hidden flex flex-col hover:border-outline-variant/50 transition-colors">
      <div className="h-56 bg-surface-container-lowest relative flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/20 via-background to-background" />
        {data.imageUrl ? (
          <img 
            src={data.imageUrl} 
            alt={`Ruas Jalan ${data.id}`} 
            className={`absolute inset-0 w-full h-full object-cover transition-all duration-700 ${
              data.hasPassed ? 'brightness-[0.35] grayscale-[40%]' : 'brightness-100'
            }`}
          />
        ) : (
          <p className="font-label-mono text-on-surface-variant/50 tracking-[0.2em] z-10 animate-pulse text-center px-6">
            MENUNGGU ANALISIS AI
          </p>
        )}
        <span className="bg-surface-variant/80 text-on-surface font-label-mono text-[12px] px-3 py-1 rounded-full absolute top-4 left-4 z-10 border border-outline-variant/30">
          Rute #{data.id}
        </span>
        {data.lightStatus === 'GREEN' && (
          <span className="absolute top-4 right-4 z-10 bg-primary text-on-primary font-label-mono text-[12px] px-3 py-1 rounded-full shadow-lg shadow-primary/30">
            AKTIF
          </span>
        )}
      </div>

      <div className="p-6 flex flex-col gap-6 flex-1">
        <div className="flex justify-between items-center border-b border-outline-variant/20 pb-4 gap-4">
          <span className="font-body-md text-on-surface-variant">Tingkat Kepadatan</span>
          <span className={`font-label-mono text-[12px] px-4 py-1.5 rounded-full border text-right ${getDensityColor(data.density)}`}>
            {densityLabel}
          </span>
        </div>

        <div>
          <p className="font-label-mono text-[12px] text-on-surface-variant uppercase tracking-wider mb-4 text-right">
            Hasil Deteksi Objek:
          </p>
          <div className="grid grid-cols-4 gap-2 text-center">
            {vehicleStats.map((stat) => (
              <div key={stat.label} className="bg-surface-container-lowest/50 rounded-lg p-2 border border-outline-variant/10">
                <p className="font-label-mono text-[10px] text-on-surface-variant mb-1">{stat.label}</p>
                <p className="font-stat-display text-2xl text-on-surface">{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <TrafficLight 
        status={data.lightStatus} 
        recommendedTime={data.greenTime} 
        remainingTime={data.remainingTime} 
        speedMultiplier={speed}
      />
    </div>
  );
}

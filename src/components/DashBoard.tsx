import { ReactNode } from 'react';

interface DashboardGridProps {
  children: ReactNode;
}

export default function DashboardGrid({ children }: DashboardGridProps) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-card-gap">
      {children}
    </div>
  );
}

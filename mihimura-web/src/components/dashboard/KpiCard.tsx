import type { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  label: string;
  value: string;
  note: string;
  trend?: string;
  tone: 'green' | 'blue' | 'orange' | 'red' | 'purple';
  icon: LucideIcon;
  /** Optional history; when omitted the space is kept so card layouts stay aligned. */
  sparkline?: number[];
}

export function KpiCard({ label, value, note, trend, tone, icon: Icon, sparkline = [] }: KpiCardProps) {
  const max = Math.max(...sparkline);
  const min = Math.min(...sparkline);
  const range = max - min || 1;
  const points = sparkline
    .map((item, index) => {
      const x = (index / Math.max(sparkline.length - 1, 1)) * 96;
      const y = 32 - ((item - min) / range) * 24;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <article className={`kpi-card tone-${tone}`}>
      <div className="kpi-card__top">
        <div className="kpi-icon">
          <Icon size={19} />
        </div>
        {trend && <span className="kpi-trend">{trend}</span>}
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-main-row">
        <strong className="kpi-value">{value}</strong>
        <svg className="kpi-sparkline" viewBox="0 0 96 36" aria-hidden="true">
          <polyline
            points={sparkline.length > 1 ? points : ''}
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <p className="kpi-note">{note}</p>
    </article>
  );
}

interface HealthGaugeProps {
  value: number;
  color: string;
}

export function HealthGauge({ value, color }: HealthGaugeProps) {
  const normalized = Math.max(0, Math.min(100, value));
  const circumference = Math.PI * 72;
  const dash = (normalized / 100) * circumference;

  return (
    <div className="health-gauge" aria-label={`Score ${normalized} out of 100`}>
      <svg viewBox="0 0 180 105" role="img">
        <path d="M 18 90 A 72 72 0 0 1 162 90" pathLength={circumference} className="health-gauge__track" />
        <path
          d="M 18 90 A 72 72 0 0 1 162 90"
          pathLength={circumference}
          className="health-gauge__value"
          style={{ stroke: color, strokeDasharray: `${dash} ${circumference}` }}
        />
      </svg>
      <div className="health-gauge__number" style={{ color }}>
        <strong>{normalized}</strong>
        <span>/100</span>
      </div>
    </div>
  );
}

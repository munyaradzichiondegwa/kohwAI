interface Props { label: string; confidence: number; }

export default function ConfidenceBar({ label, confidence }: Props) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 75 ? 'bg-brand-green' : pct >= 50 ? 'bg-brand-amber' : 'bg-brand-red';
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-800">{label}</span>
        <span className="font-semibold">{pct}%</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

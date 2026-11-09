import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  icon: LucideIcon;
  tone?: 'navy' | 'teal' | 'amber' | 'rose' | 'violet' | 'slate';
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = 'navy',
}: StatCardProps) {
  return (
    <div className={`stat-card stat-${tone}`}>
      <div className="stat-icon">
        <Icon size={20} />
      </div>
      <div className="stat-copy">
        <span className="stat-label">{label}</span>
        <span className="stat-value">{value}</span>
        {hint ? <span className="stat-hint">{hint}</span> : null}
      </div>
    </div>
  );
}

const RADIUS = 26;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Vòng tròn tiến độ — `stroke-dasharray`/`stroke-dashoffset` thay vì thanh
 * ngang, để % là thứ mắt bắt được đầu tiên. Dùng chung ở panel chat và
 * Tổng quan — tách ra đây để 2 nơi không lệch nhau khi sửa. */
export default function RadialProgress({
  percent,
  size = 64,
}: {
  percent: number;
  size?: number;
}) {
  const clamped = Math.max(0, Math.min(100, percent));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);

  return (
    <div
      className="relative flex shrink-0 items-center justify-center"
      style={{ height: size, width: size }}
      role="img"
      aria-label={`Tiến độ: ${clamped}%`}
    >
      <svg viewBox="0 0 64 64" className="-rotate-90" style={{ height: size, width: size }}>
        <circle cx="32" cy="32" r={RADIUS} fill="none" stroke="var(--border)" strokeWidth="6" />
        <circle
          cx="32"
          cy="32"
          r={RADIUS}
          fill="none"
          stroke="var(--gold)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-500"
        />
      </svg>
      <span className="absolute font-display text-sm font-semibold text-ink">{clamped}%</span>
    </div>
  );
}

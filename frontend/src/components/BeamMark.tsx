interface BeamMarkProps {
  size?: number;
  tilt?: number;
}

// The Settlement Beam, idle/level state. Positive tilt tips toward Party A (left).
export function BeamMark({ size = 32, tilt = 0 }: BeamMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="beam-mark"
      role="img"
      aria-label="Balance beam"
    >
      <path d="M50 80 L39 94 L61 94 Z" fill="var(--brass)" />
      <line x1="50" y1="48" x2="50" y2="80" stroke="var(--ink)" strokeWidth="3" />
      <g transform={`rotate(${tilt} 50 48)`}>
        <line x1="12" y1="48" x2="88" y2="48" stroke="var(--ink)" strokeWidth="4" strokeLinecap="round" />
        <circle cx="12" cy="48" r="2.5" fill="var(--party-a)" />
        <line x1="12" y1="48" x2="12" y2="60" stroke="var(--rule)" strokeWidth="1.5" />
        <path d="M4 60 Q12 71 20 60" stroke="var(--party-a)" strokeWidth="2.5" fill="none" />
        <circle cx="88" cy="48" r="2.5" fill="var(--party-b)" />
        <line x1="88" y1="48" x2="88" y2="60" stroke="var(--rule)" strokeWidth="1.5" />
        <path d="M80 60 Q88 71 96 60" stroke="var(--party-b)" strokeWidth="2.5" fill="none" />
      </g>
    </svg>
  );
}

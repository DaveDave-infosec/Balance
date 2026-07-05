import { useEffect, useState } from "react";

interface Props {
  phase: string; // reading | consensus | verdict | splitting | done
  pct: number | null;
  toDeliverer: number;
  toPayer: number;
}

const PHASES = [
  { key: "reading", label: "Reading both evidence bundles" },
  { key: "consensus", label: "Validators reaching consensus" },
  { key: "verdict", label: "Balance settles" },
  { key: "splitting", label: "Splitting the escrow" },
];
const ORDER = ["reading", "consensus", "verdict", "splitting", "done"];

function useCountUp(target: number, active: boolean) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!active) { setVal(0); return; }
    let raf = 0;
    const start = performance.now();
    const dur = 900;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setVal(Math.round(target * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active]);
  return val;
}

export function SettlementReveal({ phase, pct, toDeliverer, toPayer }: Props) {
  const idx = ORDER.indexOf(phase);
  const hasVerdict = pct !== null && (phase === "verdict" || phase === "splitting" || phase === "done");
  const tilt = hasVerdict ? (pct! - 50) * 0.45 : 0;
  const settling = hasVerdict;
  const showAmounts = phase === "splitting" || phase === "done";
  const dAmt = useCountUp(toDeliverer, showAmounts);
  const pAmt = useCountUp(toPayer, showAmounts);

  return (
    <div className="reveal">
      <div className={"reveal-beam " + (settling ? "settling" : "searching")}>
        <svg viewBox="0 0 300 200" width="300" height="200" xmlns="http://www.w3.org/2000/svg">
          <path d="M150 150 L132 182 L168 182 Z" className={"fulcrum " + (settling ? "glint" : "")} />
          <line x1="150" y1="96" x2="150" y2="150" stroke="var(--ink)" strokeWidth="4" />
          <g className="beam-rot" style={settling ? { transform: `rotate(${tilt}deg)` } : undefined}>
            <line x1="40" y1="96" x2="260" y2="96" stroke="var(--ink)" strokeWidth="6" strokeLinecap="round" />
            <line x1="40" y1="96" x2="40" y2="120" stroke="var(--rule)" strokeWidth="2" />
            <path d="M20 120 Q40 143 60 120" className="pan-a" />
            <circle cx="40" cy="96" r="4" className="dot-a" />
            <line x1="260" y1="96" x2="260" y2="120" stroke="var(--rule)" strokeWidth="2" />
            <path d="M240 120 Q260 143 280 120" className="pan-b" />
            <circle cx="260" cy="96" r="4" className="dot-b" />
          </g>
        </svg>
        {hasVerdict ? (
          <div className="reveal-pct mono">{pct}%</div>
        ) : (
          <div className="reveal-pct-label">weighing…</div>
        )}
      </div>

      <ol className="reveal-phases">
        {PHASES.map((p) => {
          const pIdx = ORDER.indexOf(p.key);
          const state = pIdx < idx ? "done" : pIdx === idx ? "active" : "todo";
          return <li key={p.key} className={"reveal-phase " + state}>{p.label}</li>;
        })}
      </ol>

      {showAmounts ? (
        <div className="reveal-amounts">
          <div className="ra a">
            <span className="split-lbl">Refunded to payer</span>
            <span className="split-amt mono">{pAmt.toLocaleString()}</span>
          </div>
          <div className="ra b">
            <span className="split-lbl">To deliverer</span>
            <span className="split-amt mono">{dAmt.toLocaleString()}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}

import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useWallet } from "../hooks/useWallet";
import type { Agreement } from "../lib/constants";
import { BeamMark } from "../components/BeamMark";
import { SettlementReveal } from "../components/SettlementReveal";
import {
  getAgreement, acceptAgreement, fundEscrow, submitDelivery,
  acceptDelivery, disputeDelivery, escrowMint, escrowBalanceOf, getProtocolFeeBps,
} from "../lib/genlayer";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
function toNum(v: any): number { return typeof v === "bigint" ? Number(v) : Number(v ?? 0); }
function short(a: string) { return a ? a.slice(0, 6) + "…" + a.slice(-4) : ""; }

function normalizeAgreement(raw: any): Agreement | null {
  if (!raw || !raw.case_id) return null;
  return {
    case_id: String(raw.case_id),
    payer: String(raw.payer || ""),
    deliverer: String(raw.deliverer || ""),
    spec: String(raw.spec || ""),
    amount: toNum(raw.amount),
    deadline: String(raw.deadline || ""),
    status: String(raw.status || ""),
    created_at: String(raw.created_at || ""),
    deliverer_submitted: String(raw.deliverer_submitted || "false"),
    deliverer_primary_url: String(raw.deliverer_primary_url || ""),
    deliverer_secondary_url: String(raw.deliverer_secondary_url || ""),
    deliverer_statement: String(raw.deliverer_statement || ""),
    payer_submitted: String(raw.payer_submitted || "false"),
    payer_primary_url: String(raw.payer_primary_url || ""),
    payer_secondary_url: String(raw.payer_secondary_url || ""),
    payer_statement: String(raw.payer_statement || ""),
    confidence_level: String(raw.confidence_level || ""),
    reasoning_summary: String(raw.reasoning_summary || ""),
    minority_note: String(raw.minority_note || ""),
    divergence_note: String(raw.divergence_note || ""),
    deliverer_evidence_assessment: String(raw.deliverer_evidence_assessment || ""),
    payer_evidence_assessment: String(raw.payer_evidence_assessment || ""),
    settled_verdict_id: String(raw.settled_verdict_id || ""),
    settled_fulfillment_pct: toNum(raw.settled_fulfillment_pct),
    settled_to_deliverer: toNum(raw.settled_to_deliverer),
    settled_to_payer: toNum(raw.settled_to_payer),
    settled_fee: toNum(raw.settled_fee),
  };
}

function EvidenceCard({ side, title, primary, secondary, statement }: {
  side: "a" | "b"; title: string; primary: string; secondary: string; statement: string;
}) {
  return (
    <div className={"evidence " + side}>
      <div className="evidence-head">{title}</div>
      <div className="evidence-row">
        <span className="evidence-label">Primary: </span>
        {primary ? <a href={primary} target="_blank" rel="noreferrer" className="mono">{primary}</a> : <span className="muted">—</span>}
      </div>
      <div className="evidence-row">
        <span className="evidence-label">Secondary: </span>
        {secondary ? <a href={secondary} target="_blank" rel="noreferrer" className="mono">{secondary}</a> : <span className="muted">—</span>}
      </div>
      {statement ? <div className="evidence-row"><span className="evidence-label">Statement: </span>{statement}</div> : null}
    </div>
  );
}

export default function AgreementDetail() {
  const { caseId } = useParams();
  const { address } = useWallet();
  const [agreement, setAgreement] = useState<Agreement | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState("");
  const [actionError, setActionError] = useState("");
  const [feeBps, setFeeBps] = useState(250);

  const [balance, setBalance] = useState<number | null>(null);
  const [minting, setMinting] = useState(false);

  const [delPrimary, setDelPrimary] = useState("");
  const [delSecondary, setDelSecondary] = useState("");
  const [delStatement, setDelStatement] = useState("");

  const [showDispute, setShowDispute] = useState(false);
  const [dispPrimary, setDispPrimary] = useState("");
  const [dispSecondary, setDispSecondary] = useState("");
  const [dispStatement, setDispStatement] = useState("");

  const [settlePhase, setSettlePhase] = useState("");

  const load = useCallback(async () => {
    if (!caseId) return;
    try {
      const raw = await getAgreement(caseId);
      const a = normalizeAgreement(raw);
      setAgreement(a);
      if (!a) setLoadError("Agreement not found.");
    } catch (e: any) {
      setLoadError(e?.message || "Failed to load agreement.");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => { setLoading(true); setLoadError(""); load(); }, [load]);
  useEffect(() => { if (caseId) load(); }, [address]);
  useEffect(() => {
    const onFocus = () => load();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [load]);
  useEffect(() => { getProtocolFeeBps().then((v) => setFeeBps(toNum(v))).catch(() => {}); }, []);

  const me = (address || "").toLowerCase();
  const isPayer = !!agreement && me === agreement.payer.toLowerCase();
  const isDeliverer = !!agreement && me === agreement.deliverer.toLowerCase();

  const refreshBalance = useCallback(async () => {
    if (!address) return;
    try { setBalance(toNum(await escrowBalanceOf(address))); } catch { /* ignore */ }
  }, [address]);

  useEffect(() => {
    if (agreement && agreement.status === "accepted" && isPayer) refreshBalance();
  }, [agreement, isPayer, refreshBalance]);

  const runAction = async (doWrite: () => Promise<any>, prevStatus: string, phases: string[]) => {
    setBusy(true); setActionError("");
    try {
      setPhase(phases[0] || "Submitting…");
      await doWrite();
      setPhase(phases[1] || "Finalizing on-chain…");
      for (let i = 0; i < 40; i++) {
        await sleep(3000);
        const raw = await getAgreement(caseId!);
        const a = normalizeAgreement(raw);
        if (a && a.status !== prevStatus) { setAgreement(a); return; }
      }
      await load();
    } catch (e: any) {
      setActionError(e?.message || "Action failed.");
    } finally {
      setBusy(false); setPhase("");
    }
  };

  const doMint = async () => {
    if (!address) return;
    setMinting(true); setActionError("");
    try {
      const before = balance ?? 0;
      await escrowMint(address, 10000, address);
      for (let i = 0; i < 20; i++) {
        await sleep(3000);
        const b = toNum(await escrowBalanceOf(address));
        if (b > before) { setBalance(b); break; }
      }
    } catch (e: any) { setActionError(e?.message || "Mint failed."); }
    finally { setMinting(false); }
  };

  const runDispute = async () => {
    if (!agreement) return;
    if (dispPrimary.trim().length === 0) { setActionError("Add at least a primary URL for your evidence."); return; }
    setActionError(""); setSettlePhase("reading");
    try {
      await disputeDelivery(caseId!, dispPrimary.trim(), dispSecondary.trim(), dispStatement.trim(), address);
      setSettlePhase("consensus");
      let settledAg: Agreement | null = null;
      for (let i = 0; i < 80; i++) {
        await sleep(3000);
        const raw = await getAgreement(caseId!);
        const ag = normalizeAgreement(raw);
        if (ag && ag.status === "settled") { settledAg = ag; break; }
      }
      if (!settledAg) throw new Error("Settlement did not finalize in time. A momentarily unreachable fetch can revert the transaction — if the status is still 'delivered', you can dispute again.");
      setAgreement(settledAg);
      setSettlePhase("verdict");
      await sleep(1700);
      setSettlePhase("splitting");
      await sleep(1500);
      setSettlePhase("done");
    } catch (e: any) {
      setActionError(e?.message || "Settlement failed.");
      setSettlePhase("");
      await load();
    }
  };

  if (loading) return <section className="form-card"><p className="muted">Loading agreement…</p></section>;
  if (loadError || !agreement) {
    return (
      <section className="form-card">
        <h1>Agreement</h1>
        <p className="form-error">{loadError || "Not found."}</p>
        <Link to="/agreements" className="detail-back">← All agreements</Link>
      </section>
    );
  }

  const a = agreement;
  const fee = Math.floor((a.amount * feeBps) / 10000);
  const distributable = a.amount - fee;
  const staticTilt = (a.settled_fulfillment_pct - 50) * 0.45;
  const revealPct = a.status === "settled" ? a.settled_fulfillment_pct : null;
  const hasReasoning = !!(a.reasoning_summary && a.reasoning_summary.length > 0);

  return (
    <section className="detail">
      <Link to="/agreements" className="detail-back">← All agreements</Link>

      <div className="detail-head">
        <h1>Agreement</h1>
        <span className={"status-badge " + a.status}>{a.status}</span>
        <span className="case-id mono muted">{a.case_id}</span>
        <button className="refresh-btn" onClick={() => load()} title="Refresh">↻</button>
      </div>

      <div className="parties">
        <div className="party a">
          <div className="party-role">Party A · Payer</div>
          <div className="party-addr mono">{short(a.payer)} {isPayer ? <span className="party-you">(you)</span> : null}</div>
        </div>
        <div className="parties-mid">
          <div className="amount-label">Escrow</div>
          <div className="amount mono">{a.amount.toLocaleString()}</div>
          <div className="amount-label">genUSDC</div>
        </div>
        <div className="party b">
          <div className="party-role">Party B · Deliverer</div>
          <div className="party-addr mono">{short(a.deliverer)} {isDeliverer ? <span className="party-you">(you)</span> : null}</div>
        </div>
      </div>

      <div className="spec-panel">
        <div className="spec-head">🔒 Locked acceptance criteria</div>
        <div className="spec-body">{a.spec}</div>
      </div>
      <div className="meta-row">
        {a.deadline ? <span>Deadline: {a.deadline}</span> : null}
        <span>Protocol fee: {(feeBps / 100).toFixed(2)}%</span>
      </div>

      {a.deliverer_submitted === "true" ? (
        <EvidenceCard side="b" title="Party B evidence — deliverable"
          primary={a.deliverer_primary_url} secondary={a.deliverer_secondary_url} statement={a.deliverer_statement} />
      ) : null}
      {a.payer_submitted === "true" ? (
        <EvidenceCard side="a" title="Party A evidence — dispute"
          primary={a.payer_primary_url} secondary={a.payer_secondary_url} statement={a.payer_statement} />
      ) : null}

      {settlePhase !== "" ? (
        <SettlementReveal
          phase={settlePhase}
          pct={revealPct}
          toDeliverer={a.settled_to_deliverer}
          toPayer={a.settled_to_payer}
        />
      ) : null}

      {a.status === "settled" && settlePhase === "" ? (
        <div className="settled">
          <div className="settled-top">
            <BeamMark size={72} tilt={staticTilt} />
            <div>
              <div className="split-lbl">Fulfillment</div>
              <div className="settled-pct mono">{a.settled_fulfillment_pct}%</div>
            </div>
          </div>
          <div className="settled-split">
            <div className="split-cell b">
              <div className="split-lbl">To deliverer</div>
              <div className="split-amt mono">{a.settled_to_deliverer.toLocaleString()}</div>
            </div>
            <div className="split-cell a">
              <div className="split-lbl">Refunded to payer</div>
              <div className="split-amt mono">{a.settled_to_payer.toLocaleString()}</div>
            </div>
          </div>
          <div className="meta-row">
            <span>Protocol fee: {a.settled_fee.toLocaleString()} genUSDC</span>
            <span className="mono">{a.settled_verdict_id === "accepted_in_full" ? "accepted in full" : "consensus"}</span>
          </div>
        </div>
      ) : null}

      {hasReasoning ? (
        <div className="verdict-panel">
          <div className="spec-head">Consensus reasoning</div>
          <p className="verdict-reasoning">{a.reasoning_summary}</p>
          <div className="verdict-grid">
            <div><span className="split-lbl">Confidence</span><div>{a.confidence_level}</div></div>
          </div>
          {a.divergence_note ? <p className="verdict-note"><span className="evidence-label">Where the bundles diverged: </span>{a.divergence_note}</p> : null}
          {a.deliverer_evidence_assessment ? <p className="verdict-note"><span className="evidence-label" style={{ color: "var(--party-b)" }}>Deliverer evidence: </span>{a.deliverer_evidence_assessment}</p> : null}
          {a.payer_evidence_assessment ? <p className="verdict-note"><span className="evidence-label" style={{ color: "var(--party-a)" }}>Payer evidence: </span>{a.payer_evidence_assessment}</p> : null}
          {a.minority_note ? <div className="minority"><div className="split-lbl">Minority view, preserved</div><p>{a.minority_note}</p></div> : null}
        </div>
      ) : null}

      {a.status === "created" ? (
        <div className="action-panel">
          {isDeliverer ? (
            <>
              <h2>Accept the criteria</h2>
              <p>You are Party B. Accepting makes the locked criteria binding for both sides — the yardstick can't change afterward.</p>
              <div className="btn-row">
                <button className="btn btn-primary" disabled={busy}
                  onClick={() => runAction(() => acceptAgreement(caseId!, address), "created", ["Recording acceptance…", "Finalizing…"])}>
                  {busy ? "Working…" : "Accept agreement"}
                </button>
              </div>
            </>
          ) : (
            <p className="action-wait">Waiting for the deliverer to accept the locked criteria.</p>
          )}
        </div>
      ) : null}

      {a.status === "accepted" ? (
        <div className="action-panel">
          {isPayer ? (
            <>
              <h2>Fund the escrow</h2>
              <p className="balance-line">
                Your balance: <span className="mono">{balance === null ? "…" : balance.toLocaleString()}</span> genUSDC · needed: <span className="mono">{a.amount.toLocaleString()}</span>
              </p>
              <div className="btn-row">
                <button className="btn btn-primary" disabled={busy || (balance !== null && balance < a.amount)}
                  onClick={() => runAction(() => fundEscrow(caseId!, address), "accepted", ["Funding escrow…", "Finalizing…"])}>
                  {busy ? "Working…" : "Fund " + a.amount.toLocaleString() + " genUSDC"}
                </button>
                <button className="btn btn-ghost" disabled={minting} onClick={doMint}>
                  {minting ? "Minting…" : "Get 10,000 test genUSDC"}
                </button>
              </div>
            </>
          ) : (
            <p className="action-wait">Waiting for the payer to fund the escrow.</p>
          )}
        </div>
      ) : null}

      {a.status === "active" ? (
        <div className="action-panel">
          {isDeliverer ? (
            <>
              <h2>Submit your deliverable</h2>
              <p>Link the resources the judge can fetch and read — a repo, a deployed URL, a document. A written statement is optional context, but the judge verifies claims against the actual resources.</p>
              <label className="field">
                <span className="field-label">Primary URL (repo, deployment, or file)</span>
                <input className="input mono" placeholder="https://github.com/…" value={delPrimary} onChange={(e) => setDelPrimary(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Secondary URL (optional)</span>
                <input className="input mono" placeholder="https://…" value={delSecondary} onChange={(e) => setDelSecondary(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Statement (optional)</span>
                <textarea className="input" rows={3} value={delStatement} onChange={(e) => setDelStatement(e.target.value)} />
              </label>
              <div className="btn-row">
                <button className="btn btn-primary" disabled={busy || delPrimary.trim().length === 0}
                  onClick={() => runAction(() => submitDelivery(caseId!, delPrimary.trim(), delSecondary.trim(), delStatement.trim(), address), "active", ["Submitting delivery…", "Finalizing…"])}>
                  {busy ? "Working…" : "Submit delivery"}
                </button>
              </div>
            </>
          ) : (
            <p className="action-wait">Waiting for the deliverer to submit the deliverable.</p>
          )}
        </div>
      ) : null}

      {a.status === "delivered" && settlePhase === "" ? (
        <div className="action-panel">
          {isPayer ? (
            <>
              <h2>Review the delivery</h2>
              <p>Accept in full to release the escrow to the deliverer, or dispute. Disputing runs the consensus and splits the escrow by the fulfillment percentage in a single, irreversible transaction.</p>
              <div className="btn-row">
                <button className="btn btn-primary" disabled={busy}
                  onClick={() => runAction(() => acceptDelivery(caseId!, address), "delivered", ["Releasing escrow…", "Finalizing…"])}>
                  {busy ? "Working…" : "Accept — release " + distributable.toLocaleString() + " genUSDC"}
                </button>
                <button className="btn btn-ghost" disabled={busy} onClick={() => setShowDispute((s) => !s)}>
                  {showDispute ? "Cancel dispute" : "Dispute"}
                </button>
              </div>
              {showDispute ? (
                <div style={{ marginTop: "16px" }}>
                  <p>Submit your own evidence. When you dispute, the judge fetches both bundles and the locked criteria, decides how much was fulfilled, and the escrow splits — all in one transaction. A broken or empty resource counts as a signal.</p>
                  <label className="field">
                    <span className="field-label">Primary URL</span>
                    <input className="input mono" placeholder="https://…" value={dispPrimary} onChange={(e) => setDispPrimary(e.target.value)} />
                  </label>
                  <label className="field">
                    <span className="field-label">Secondary URL (optional)</span>
                    <input className="input mono" placeholder="https://…" value={dispSecondary} onChange={(e) => setDispSecondary(e.target.value)} />
                  </label>
                  <label className="field">
                    <span className="field-label">Statement (optional)</span>
                    <textarea className="input" rows={3} value={dispStatement} onChange={(e) => setDispStatement(e.target.value)} />
                  </label>
                  <div className="btn-row">
                    <button className="btn btn-brass" disabled={dispPrimary.trim().length === 0} onClick={runDispute}>
                      Dispute &amp; settle
                    </button>
                  </div>
                </div>
              ) : null}
            </>
          ) : (
            <p className="action-wait">Waiting for the payer to accept or dispute the delivery.</p>
          )}
        </div>
      ) : null}

      {actionError ? <div className="form-error">{actionError}</div> : null}
      {phase ? <div className="form-phase mono">{phase}</div> : null}
    </section>
  );
}

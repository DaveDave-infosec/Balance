import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useWallet } from "../hooks/useWallet";
import type { Agreement } from "../lib/constants";
import { getAgreementsByParty, escrowBalanceOf, escrowMint } from "../lib/genlayer";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
function toNum(v: any): number { return typeof v === "bigint" ? Number(v) : Number(v ?? 0); }
function truncate(s: string, n: number) { return s.length > n ? s.slice(0, n) + "…" : s; }

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
    settled_verdict_id: String(raw.settled_verdict_id || ""),
    settled_fulfillment_pct: toNum(raw.settled_fulfillment_pct),
    settled_to_deliverer: toNum(raw.settled_to_deliverer),
    settled_to_payer: toNum(raw.settled_to_payer),
    settled_fee: toNum(raw.settled_fee),
  };
}

export default function AgreementsList() {
  const { address, connect, connecting } = useWallet();
  const [items, setItems] = useState<Agreement[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [balance, setBalance] = useState<number | null>(null);
  const [minting, setMinting] = useState(false);

  const load = useCallback(async (silent?: boolean) => {
    if (!address) return;
    if (!silent) setLoading(true);
    setError("");
    try {
      const raw = await getAgreementsByParty(address);
      const arr = Array.isArray(raw) ? raw : [];
      const norm = arr.map(normalizeAgreement).filter((x): x is Agreement => x !== null);
      setItems(norm);
      setBalance(toNum(await escrowBalanceOf(address)));
    } catch (e: any) {
      setError(e?.message || "Failed to load agreements.");
    } finally {
      setLoading(false);
    }
  }, [address]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const onFocus = () => load(true);
    window.addEventListener("focus", onFocus);
    const id = setInterval(() => load(true), 6000);
    return () => { window.removeEventListener("focus", onFocus); clearInterval(id); };
  }, [load]);

  const doMint = async () => {
    if (!address) return;
    setMinting(true); setError("");
    try {
      const before = balance ?? 0;
      await escrowMint(address, 10000, address);
      for (let i = 0; i < 20; i++) {
        await sleep(3000);
        const b = toNum(await escrowBalanceOf(address));
        if (b > before) { setBalance(b); break; }
      }
    } catch (e: any) { setError(e?.message || "Mint failed."); }
    finally { setMinting(false); }
  };

  if (!address) {
    return (
      <section className="form-card">
        <h1>Agreements</h1>
        <p className="muted">Connect your wallet to see the agreements you're part of.</p>
        <button className="btn btn-primary" onClick={connect} disabled={connecting}>
          {connecting ? "Connecting…" : "Connect Wallet"}
        </button>
      </section>
    );
  }

  return (
    <section className="detail">
      <div className="list-head">
        <h1>Your agreements</h1>
        <div className="list-head-actions">
          <button className="refresh-btn" onClick={() => load()} title="Refresh">↻</button>
          <Link to="/new" className="btn btn-primary">New agreement</Link>
        </div>
      </div>

      <div className="wallet-summary">
        <span className="balance-line">Balance: <span className="mono">{balance === null ? "…" : balance.toLocaleString()}</span> genUSDC</span>
        <button className="btn btn-ghost" disabled={minting} onClick={doMint}>
          {minting ? "Minting…" : "Get 10,000 test genUSDC"}
        </button>
      </div>

      {loading ? <p className="muted">Loading…</p> : null}
      {error ? <div className="form-error">{error}</div> : null}
      {!loading && items.length === 0 ? <p className="muted">No agreements yet. Create one to get started.</p> : null}

      <div className="agreement-rows">
        {items.map((a) => {
          const role = a.payer.toLowerCase() === address.toLowerCase() ? "Payer" : "Deliverer";
          return (
            <Link key={a.case_id} to={"/agreement/" + a.case_id} className={"agreement-row " + (role === "Payer" ? "as-a" : "as-b")}>
              <div className="ar-left">
                <span className={"status-badge " + a.status}>{a.status}</span>
                <span className="ar-spec">{truncate(a.spec, 96)}</span>
              </div>
              <div className="ar-right">
                <span className="ar-role">{role}</span>
                <span className="ar-amount mono">{a.amount.toLocaleString()} genUSDC</span>
                <span className="ar-id mono muted">{a.case_id}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

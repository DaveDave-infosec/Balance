import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useWallet } from "../hooks/useWallet";
import { createAgreement, getCaseCount } from "../lib/genlayer";

const ADDR = /^0x[0-9a-fA-F]{40}$/;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function CreateAgreement() {
  const { address, connect, connecting } = useWallet();
  const navigate = useNavigate();

  const [spec, setSpec] = useState("");
  const [amount, setAmount] = useState("");
  const [deadline, setDeadline] = useState("");
  const [deliverer, setDeliverer] = useState("");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState("");
  const [error, setError] = useState("");

  const amountNum = parseInt(amount, 10);
  const delivererValid = ADDR.test(deliverer.trim());
  const notSelf =
    delivererValid && !!address &&
    deliverer.trim().toLowerCase() !== address.toLowerCase();
  const canSubmit =
    !!address &&
    spec.trim().length > 0 &&
    Number.isFinite(amountNum) && amountNum > 0 &&
    delivererValid && notSelf &&
    !busy;

  const onSubmit = async () => {
    setError("");
    if (!address) { setError("Connect your wallet first."); return; }
    if (spec.trim().length === 0) { setError("Describe the deliverable and its acceptance criteria."); return; }
    if (!Number.isFinite(amountNum) || amountNum <= 0) { setError("Enter an escrow amount greater than zero."); return; }
    if (!delivererValid) { setError("Enter a valid deliverer wallet address (0x + 40 hex)."); return; }
    if (!notSelf) { setError("The deliverer must be a different wallet than yours."); return; }

    setBusy(true);
    setPhase("Locking the agreement on-chain\u2026");
    try {
      const createdAt = new Date().toISOString();
      const countBefore = Number(await getCaseCount());
      const returned = await createAgreement(
        spec.trim(), amountNum, deadline || "", deliverer.trim(), createdAt, address,
      );
      const asStr = typeof returned === "string" ? returned : String(returned);
      if (asStr.startsWith("case_")) {
        navigate("/agreement/" + asStr);
        return;
      }
      setPhase("Waiting for finalization\u2026");
      for (let i = 0; i < 40; i++) {
        await sleep(3000);
        const countAfter = Number(await getCaseCount());
        if (countAfter > countBefore) {
          navigate("/agreement/case_" + (countAfter - 1));
          return;
        }
      }
      setError("The agreement is taking longer than expected to finalize. Check the Agreements page shortly.");
    } catch (e: any) {
      setError(e?.message || "Failed to create the agreement.");
    } finally {
      setBusy(false);
      setPhase("");
    }
  };

  if (!address) {
    return (
      <section className="form-card">
        <h1>Create an agreement</h1>
        <p className="muted">Connect your wallet to draft an agreement. You'll be Party A &mdash; the payer.</p>
        <button className="btn btn-primary" onClick={connect} disabled={connecting}>
          {connecting ? "Connecting\u2026" : "Connect Wallet"}
        </button>
      </section>
    );
  }

  return (
    <section className="form-card">
      <h1>Create an agreement</h1>
      <p className="muted">
        You are <span className="party-a-tag">Party A &mdash; the payer</span>. You draft the
        acceptance criteria and lock them on-chain. Party B (the deliverer) must accept the
        same criteria before the agreement goes active &mdash; neither side can change the
        yardstick afterward.
      </p>

      <label className="field">
        <span className="field-label">Deliverable &amp; acceptance criteria</span>
        <textarea
          className="input"
          rows={7}
          placeholder={"e.g.\n- Public GitHub repo containing a React + TypeScript todo app\n- Working auth flow: a user can sign up and log in\n- Deployed URL returns HTTP 200 and renders the todo list\n- README documents how to run it locally"}
          value={spec}
          onChange={(e) => setSpec(e.target.value)}
        />
      </label>

      <div className="guide">
        <div className="guide-col guide-good">
          <div className="guide-head">Write criteria a judge can verify</div>
          <ul>
            <li>Repo contains a working signup + login flow</li>
            <li>Deployed URL returns HTTP 200 at /dashboard</li>
            <li>README documents the setup steps</li>
            <li>File includes all five requested sections</li>
          </ul>
        </div>
        <div className="guide-col guide-bad">
          <div className="guide-head">Avoid criteria it can't check</div>
          <ul>
            <li>"The app feels premium"</li>
            <li>"Modern, clean design"</li>
            <li>"Delivered on time"</li>
            <li>Anything not visible in a fetchable URL, repo, or file</li>
          </ul>
        </div>
      </div>
      <p className="hint">
        The judge can only evaluate web-fetchable text, code, and data. Criteria it can read
        and check against real resources produce a fair fulfillment percentage.
      </p>

      <div className="field-row">
        <label className="field">
          <span className="field-label">Escrow amount (genUSDC)</span>
          <input
            className="input mono"
            type="number"
            min={1}
            step={1}
            placeholder="1000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </label>
        <label className="field">
          <span className="field-label">Deadline (optional)</span>
          <input
            className="input"
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
          />
        </label>
      </div>

      <label className="field">
        <span className="field-label">Party B &mdash; deliverer wallet address</span>
        <input
          className="input mono"
          placeholder="0x…"
          value={deliverer}
          onChange={(e) => setDeliverer(e.target.value)}
        />
        {deliverer.length > 0 && !delivererValid ? (
          <span className="field-err">Enter a valid address (0x followed by 40 hex characters).</span>
        ) : null}
        {delivererValid && !notSelf ? (
          <span className="field-err">The deliverer must be a different wallet than yours.</span>
        ) : null}
      </label>

      <div className="field">
        <span className="field-label">Party A &mdash; payer (you)</span>
        <span className="mono readonly-addr">{address}</span>
      </div>

      {error ? <div className="form-error">{error}</div> : null}
      {phase ? <div className="form-phase mono">{phase}</div> : null}

      <div className="form-actions">
        <button className="btn btn-primary" onClick={onSubmit} disabled={!canSubmit}>
          {busy ? "Working\u2026" : "Lock agreement on-chain"}
        </button>
      </div>
    </section>
  );
}

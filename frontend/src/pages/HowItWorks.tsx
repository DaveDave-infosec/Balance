import { BeamMark } from "../components/BeamMark";
import { BALANCE_CONTRACT_ADDRESS } from "../lib/constants";

export default function HowItWorks() {
  return (
    <section className="doc">
      <div className="doc-hero">
        <BeamMark size={80} />
        <h1>How Balance works</h1>
        <p className="lead">
          Balance settles disputes over digital work. When a payer and a deliverer
          disagree about whether a deliverable was met, GenLayer's validators read the
          evidence, judge how much of the agreed criteria was actually fulfilled, and the
          escrow splits the funds by that percentage — automatically and irreversibly.
          No arbitrator holds the money. The consensus is the settlement.
        </p>
      </div>

      <h2>Using it, step by step</h2>
      <ol className="steps">
        <li><strong>Create.</strong> The payer (Party A) drafts the acceptance criteria, locks them on-chain, and names the deliverer and the escrow amount.</li>
        <li><strong>Accept.</strong> The deliverer (Party B) reviews and accepts the same criteria. Neither side can change the yardstick afterward.</li>
        <li><strong>Fund.</strong> The payer deposits genUSDC into escrow. The agreement goes active.</li>
        <li><strong>Deliver.</strong> The deliverer submits the work as evidence the judge can fetch — a repo, a deployed URL, a document.</li>
        <li><strong>Accept or dispute.</strong> The payer accepts in full, or disputes. A dispute fetches both sides' evidence, reaches consensus on the fulfillment percentage, and splits the escrow — all in one transaction.</li>
      </ol>

      <h2>How the judge stays fair</h2>
      <p>
        Both parties submit their evidence independently. The judge fetches both bundles
        plus the locked criteria and verifies claims against the actual resources — it
        never takes either side's written description as fact. Where the two bundles
        diverge, the divergence itself is evidence, and a broken, empty, or missing
        resource counts against whatever claim depends on it.
      </p>
      <p>
        This is why criteria must be checkable against readable evidence. "Repo contains a
        working login flow" can be verified; "the app feels premium" cannot — and
        subjective criteria don't produce the consistent consensus that a fair split
        depends on.
      </p>

      <h2>Settlement is atomic</h2>
      <p>
        There is no separate settlement step and no privileged party who triggers it. The
        same transaction that judges the evidence also moves the money: consensus lands on
        a fulfillment percentage and the escrow splits by it, irreversibly, in one step.
        If a resource is momentarily unreachable the whole transaction simply reverts —
        nothing partial is ever recorded — and the dispute can be retried.
      </p>

      <h2>Honest limitations</h2>
      <div className="limitations">
        <div className="lim">
          <h3>Digital work only</h3>
          <p>Balance judges what a validator can fetch and read — code, documents, URLs. Offline or physical work (construction, in-person consulting, events) is out of scope.</p>
        </div>
        <div className="lim">
          <h3>The minority view</h3>
          <p>The "minority view, preserved" in each settlement is the strongest good-faith case for a different percentage, articulated by the model — not a transcript of dissenting validators. It keeps the reasoning honest; it is not a raw vote spread.</p>
        </div>
        <div className="lim">
          <h3>Evidence must render as text</h3>
          <p>The judge reads the rendered text of a URL. A heavy client-side app that shows little without interaction may read thin — link a repo or a readable page alongside it.</p>
        </div>
        <div className="lim">
          <h3>Testnet</h3>
          <p>genUSDC is a mock settlement token for demonstration on the GenLayer Studio network.</p>
        </div>
      </div>

      <h2>Under the hood</h2>
      <p>
        Balance runs on a single Python Intelligent Contract on GenLayer Studio (chain
        61999). It holds the escrow, records each agreement and its locked criteria, and —
        on a dispute — fetches both parties' evidence deterministically, reasons to a
        fulfillment percentage by validator consensus, and splits the escrow, all in the
        same transaction. It is the only thing that moves the money, and only ever by the
        consensus result.
      </p>
      <div className="addr-line"><span className="addr-label">Contract: </span><span className="mono">{BALANCE_CONTRACT_ADDRESS}</span></div>
    </section>
  );
}

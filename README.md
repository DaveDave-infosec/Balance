# Balance

**Consensus-based adaptive settlement for digital-work disputes on the GenLayer Studio Network.**

> Not every dispute has a winner. Every dispute deserves a balance.

Balance is proportional escrow. Instead of binary release-or-refund, GenLayer validators judge how much of a digital deliverable was actually fulfilled, and the contract splits the escrowed funds by that consensus percentage — automatically, on-chain, and irreversibly.

## The load-bearing idea

When consensus reaches a verdict, something irreversible and valuable happens automatically: the escrow splits by the fulfillment percentage. Remove the decentralized consensus and a single arbitrator controls the money — which no counterparty would trust. **The consensus *is* the settlement authority.**

Settlement is atomic: the same transaction that judges the evidence also moves the money. There is no relay and no privileged trigger.

## How it works

1. **Create** — the payer drafts acceptance criteria, locks them on-chain, and names the deliverer and escrow amount.
2. **Accept** — the deliverer accepts the same criteria. Neither side can change the yardstick afterward.
3. **Fund** — the payer deposits genUSDC into escrow.
4. **Deliver** — the deliverer submits the work as evidence the judge can fetch (repo, deployment, document).
5. **Accept or dispute** — the payer accepts in full, or disputes. A dispute fetches both parties' evidence, reaches consensus on a fulfillment percentage, and splits the escrow — all in one transaction.

Both parties submit evidence independently. The judge verifies claims against the actual fetched resources — a broken, empty, or missing resource counts against the claim that depends on it — and preserves a minority view alongside the verdict.

## Architecture

- **`contracts/balance.py`** — a single Python Intelligent Contract on GenLayer Studio. It holds the escrow, records each agreement and its locked criteria, and on dispute fetches evidence (`gl.eq_principle.strict_eq`), reasons to a fulfillment percentage by validator consensus (`gl.eq_principle.prompt_comparative`), and splits the escrow — atomically. It is the only thing that moves the money, and only by the consensus result.
- **`frontend/`** — React + TypeScript + Vite, using `genlayer-js`.

**Deployed contract:** `0x928f9A5a12403dd4cab955e861dF2d0CC494e2C9`
**Network:** GenLayer Studio (chain ID 61999). genUSDC is a mock settlement token for the testnet.

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

## Scope & honest limitations

- **Digital work only.** Balance judges what a validator can fetch and read — code, documents, URLs. Offline or physical work is out of scope.
- **Evidence must render as text.** The judge reads the rendered text of a URL; heavy client-side apps may read thin, so pair a deployment with its repo.
- **The minority view** is the model's steelman of the strongest dissenting percentage, not a transcript of validator votes.
- **Testnet.** genUSDC is a mock settlement token.

## Validation

Tested across the full fairness range on real projects:

| Scenario | Fulfillment |
|---|---|
| Gaming attempt (wrong repo submitted) | 4% |
| Partial deliverable | 60% |
| Complete project, documented limitation | 74–80% |
| Complete project | 92% |

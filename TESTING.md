# Balance — Contract Tests

These tests exercise the real `contracts/balance.py` Intelligent Contract in a
local GenVM. No skips, no copied logic — every assertion runs against the actual
deployed contract code.

## What they prove

| Test | Property |
|---|---|
| `test_owner_is_deployer` | Owner is the deploying wallet (`gl.message.sender_address`), not a passed-in address. |
| `test_only_owner_can_mint` | The testnet token faucet is owner-gated; a non-owner mint reverts. |
| `test_create_requires_distinct_parties` | Payer and deliverer must differ. |
| `test_create_records_sender_as_payer` | The payer is recorded from the transaction sender, not a caller-supplied argument. |
| `test_only_deliverer_can_accept` | Only the named deliverer can accept the locked criteria. |
| `test_only_payer_can_fund` | Only the payer can fund the escrow. |
| `test_fund_requires_balance_then_activates` | Funding requires sufficient balance and activates the agreement. |
| `test_cannot_fund_before_accept` | The lifecycle can't be skipped — no funding before acceptance. |
| `test_cannot_deliver_before_active` | No delivery before the escrow is funded. |
| `test_cannot_dispute_before_delivered` | No dispute before a delivery exists. |
| `test_only_deliverer_can_submit` | Only the deliverer can submit the deliverable. |
| `test_accept_in_full_pays_and_settles` | Accept-in-full releases the full amount (minus fee) and settles at 100%. |
| `test_only_payer_can_accept_delivery` | Only the payer can accept a delivery. |
| `test_dispute_settles_by_consensus_pct` | A dispute splits the escrow by the consensus fulfillment % (60% → 585/390), skims the fee, and records the evidence hash. |
| `test_dispute_low_verdict_refunds_payer` | A low verdict (10%) refunds the payer the majority of the escrow. |

Every privileged action is authorized from the transaction sender; no
caller-supplied identity, evidence, or outcome can drive settlement. The split
is computed on-chain from the consensus verdict, and the fetched evidence is
`sha256`-hashed and recorded immutably on the settled case.

## Why the direct runner

Balance is a single Intelligent Contract, so the tests use `genlayer-test`'s
**direct in-process runner** (`direct_vm` / `direct_deploy`) — a real GenVM, no
simulator RPC and no cross-contract routing needed. Contract logic runs for
real; only the two external nondet inputs of a dispute are mocked:

- `direct_vm.mock_web(...)` supplies the fetched evidence text (`gl.nondet.web.render`).
- `direct_vm.mock_llm(...)` supplies the consensus verdict JSON (`gl.nondet.exec_prompt` inside `gl.eq_principle.prompt_comparative`).

Verdict content is mocked so the split is deterministic; the settlement logic,
guards, fee math, and evidence hashing under test all execute against the real
contract.

## Running

```bash
pip install "genlayer-test[sim]==0.29.2"
python -m pytest tests/test_guards.py -v
```

The first run caches the pinned GenVM SDK (`v0.2.16`); later runs are offline.
Expected: `15 passed`.

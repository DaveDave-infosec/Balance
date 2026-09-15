# Deployment & Provenance

This document establishes the provenance chain for the **Balance** protocol:
source code → deployed contract → deploy transaction → live on-chain activity.
Anyone can verify each link independently on the GenLayer Studio explorer.

## Network

| Field | Value |
|-------|-------|
| Network | GenLayer Studio Network |
| Chain ID | 61999 (`0xF22F`) |
| RPC endpoint | https://studio.genlayer.com/api |
| Explorer | https://explorer-studio.genlayer.com |

## Deployed contract

| Field | Value |
|-------|-------|
| Contract | Balance (single Intelligent Contract) |
| Source of truth | [`contracts/balance.py`](./contracts/balance.py) |
| Address | `0x478e947c013C42114C7Ed33E02F30ae8E0B6D6ea` |
| Constructor arg | `protocol_fee_bps = 250` (2.50%) |
| Explorer | https://explorer-studio.genlayer.com/address/0x478e947c013C42114C7Ed33E02F30ae8E0B6D6ea |

The code deployed at the address above is viewable on the explorer and is
byte-identical to [`contracts/balance.py`](./contracts/balance.py) in this
repository at the commit that ships this file. GenLayer Intelligent Contracts
are deployed from Python source, so the on-chain code and the repo source can
be compared directly — no separate build/bytecode step to reconcile.

## Provenance chain

1. **Source** — `contracts/balance.py` in this repo (committed alongside this
   document).
2. **Deployment** — deployed to the address above via the deploy transaction
   below, signed from the deployer wallet, which is recorded on-chain as the
   contract owner.
3. **Live activity** — the contract has processed real transactions; a
   representative one is cited below.

### Deploy transaction

| Field | Value |
|-------|-------|
| Tx hash | `0x292c67bf2996704ee4b6dc0c185d839dd625fdf8a43314d7ca7c13d24947e7ca` |
| Explorer | https://explorer-studio.genlayer.com/tx/0x292c67bf2996704ee4b6dc0c185d839dd625fdf8a43314d7ca7c13d24947e7ca |

### Representative live transaction

A `create_agreement` write, signed via MetaMask (verified injected signer),
creating an on-chain agreement (`case_2`).

| Field | Value |
|-------|-------|
| Action | `create_agreement` |
| Tx hash | `0xac389275f845a4e886a66288222cc26f0875d40cbcc35dbddf796791cb4b1442` |
| Explorer | https://explorer-studio.genlayer.com/tx/0xac389275f845a4e886a66288222cc26f0875d40cbcc35dbddf796791cb4b1442 |

## How to verify

1. Open the contract on the explorer (link above) and read the deployed code.
2. Compare it against [`contracts/balance.py`](./contracts/balance.py) at this commit.
3. Confirm the deploy tx created that address, and that the live tx was
   executed successfully against it.

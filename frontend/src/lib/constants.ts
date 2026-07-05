// Balance configuration.
// GenLayer Studio Network.
export const STUDIO_CHAIN_ID = 61999;
export const STUDIO_CHAIN_HEX = "0xF22F";

// Deployed Intelligent Contracts (both Python, both on Studio). Env vars
// (VITE_ prefix) override for Vercel; fallbacks are our live testnet deploys.
export const BALANCE_CONTRACT_ADDRESS =
  import.meta.env.VITE_BALANCE_CONTRACT_ADDRESS ||
  "0x928f9A5a12403dd4cab955e861dF2d0CC494e2C9";

// Optional admin wallet (for a faucet/admin panel). Lowercased for comparison.
export const OWNER_ADDRESS = (import.meta.env.VITE_OWNER_ADDRESS || "").toLowerCase();

// Money is whole genUSDC units on-chain (no 18-decimal wei); the frontend
// passes plain integers straight through.

// Agreement lifecycle states, mirrored from balance_escrow.py.
export type AgreementStatus =
  | "created"
  | "accepted"
  | "active"
  | "delivered"
  | "disputed"
  | "settled";

// Shape returned by escrow.get_agreement (mirrors _build_agreement).
export interface Agreement {
  case_id: string;
  payer: string;
  deliverer: string;
  spec: string;
  amount: number;
  deadline: string;
  status: AgreementStatus | string;
  created_at: string;
  deliverer_submitted: string;
  deliverer_primary_url: string;
  deliverer_secondary_url: string;
  deliverer_statement: string;
  payer_submitted: string;
  payer_primary_url: string;
  payer_secondary_url: string;
  payer_statement: string;
  confidence_level?: string;
  reasoning_summary?: string;
  minority_note?: string;
  divergence_note?: string;
  deliverer_evidence_assessment?: string;
  payer_evidence_assessment?: string;
  settled_verdict_id: string;
  settled_fulfillment_pct: number;
  settled_to_deliverer: number;
  settled_to_payer: number;
  settled_fee: number;
}

// Shape returned by judge.get_verdict (mirrors _build_verdict).
export interface Verdict {
  verdict_id: string;
  case_id: string;
  fulfillment_pct: number;
  confidence_level: string;
  deliverer_evidence_assessment: string;
  payer_evidence_assessment: string;
  divergence_note: string;
  reasoning_summary: string;
  minority_note: string;
  spec_used: string;
  deliverer_primary_url: string;
  deliverer_secondary_url: string;
  deliverer_statement: string;
  payer_primary_url: string;
  payer_secondary_url: string;
  payer_statement: string;
  payer_address: string;
  deliverer_address: string;
  requested_at: string;
}

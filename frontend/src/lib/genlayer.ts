import { createClient, createAccount, generatePrivateKey as _generatePrivateKey } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { BALANCE_CONTRACT_ADDRESS, STUDIO_CHAIN_HEX } from "./constants";

export const publicClient: any = createClient({ chain: studionet } as any);

let _wallet: any = null;
let _mode: "session" | "metamask" = "session";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Auto-recover from transient RPC failures (429 rate limits, dropped fetches).
async function withRetry<T>(fn: () => Promise<T>, tries = 5): Promise<T> {
  let delay = 2500;
  for (let i = 0; i < tries; i++) {
    try {
      return await fn();
    } catch (e: any) {
      const msg = String(e?.message || e);
      const transient = /429|rate limit|Failed to fetch|fetch failed|Load failed|network|timeout/i.test(msg);
      if (!transient || i === tries - 1) throw e;
      const m = msg.match(/retry_after_seconds["\s:]+(\d+)/i);
      const wait = m ? (parseInt(m[1], 10) + 1) * 1000 : delay;
      await sleep(wait);
      delay = Math.min(delay * 2, 20000);
    }
  }
  throw new Error("unreachable");
}

export function generatePrivateKey(): string {
  return _generatePrivateKey();
}

export function setSessionWallet(privateKey: string): string {
  const acct = createAccount(privateKey as `0x${string}`);
  _wallet = createClient({ chain: studionet, account: acct } as any);
  _mode = "session";
  return acct.address as string;
}

export function setMetaMaskWallet(address: string): string {
  _wallet = createClient({ chain: studionet, account: address as `0x${string}` } as any);
  _mode = "metamask";
  return address;
}

export async function ensureChain(): Promise<void> {
  const eth = (window as any).ethereum;
  if (!eth) throw new Error("MetaMask not detected.");
  const cur = await eth.request({ method: "eth_chainId" });
  if (typeof cur === "string" && cur.toLowerCase() === STUDIO_CHAIN_HEX.toLowerCase()) return;
  try {
    await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: STUDIO_CHAIN_HEX }] });
  } catch (e: any) {
    if (e?.code === 4902) {
      await eth.request({
        method: "wallet_addEthereumChain",
        params: [{
          chainId: STUDIO_CHAIN_HEX,
          chainName: "GenLayer Studio",
          nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
          rpcUrls: ["https://studio.genlayer.com/api"],
          blockExplorerUrls: ["https://explorer-studio.genlayer.com"],
        }],
      });
    } else {
      throw new Error("Failed to switch wallet to Studio Network. " + (e?.message || ""));
    }
  }
}

export async function connectMetaMask(): Promise<string> {
  const eth = (window as any).ethereum;
  if (!eth) throw new Error("MetaMask not detected. Use the in-app session wallet instead.");
  const accts: string[] = await eth.request({ method: "eth_requestAccounts" });
  await ensureChain();
  return setMetaMaskWallet(accts[0]);
}

async function balanceWrite(functionName: string, args: any[]) {
  if (!_wallet) throw new Error("No wallet ready — reload the page.");
  if (_mode === "metamask") await ensureChain();
  return await withRetry(() =>
    _wallet.writeContract({ address: BALANCE_CONTRACT_ADDRESS, functionName, args, value: 0n } as any)
  );
}

async function read(functionName: string, args: any[]) {
  return await withRetry(() =>
    publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName, args } as any)
  );
}

export async function escrowMint(toAddress: string, amount: number, _caller?: string) {
  return balanceWrite("mint", [toAddress, amount]);
}
export async function createAgreement(spec: string, amount: number, deadline: string, delivererAddress: string, createdAt: string, _caller?: string) {
  return balanceWrite("create_agreement", [spec, amount, deadline, delivererAddress, createdAt]);
}
export async function acceptAgreement(caseId: string, _caller?: string) {
  return balanceWrite("accept_agreement", [caseId]);
}
export async function fundEscrow(caseId: string, _caller?: string) {
  return balanceWrite("fund_escrow", [caseId]);
}
export async function submitDelivery(caseId: string, primaryUrl: string, secondaryUrl: string, statement: string, _caller?: string) {
  return balanceWrite("submit_delivery", [caseId, primaryUrl, secondaryUrl, statement]);
}
export async function acceptDelivery(caseId: string, _caller?: string) {
  return balanceWrite("accept_delivery", [caseId]);
}
export async function disputeDelivery(caseId: string, primaryUrl: string, secondaryUrl: string, statement: string, _caller?: string) {
  return balanceWrite("dispute_delivery", [caseId, primaryUrl, secondaryUrl, statement]);
}
export async function cancelAgreement(caseId: string, _caller?: string) {
  return balanceWrite("cancel_agreement", [caseId]);
}
export async function reclaimExpired(caseId: string, _caller?: string) {
  return balanceWrite("reclaim_expired", [caseId]);
}
export async function claimStaleDelivery(caseId: string, _caller?: string) {
  return balanceWrite("claim_stale_delivery", [caseId]);
}

export async function escrowBalanceOf(address: string) {
  return await read("balance_of", [address]);
}
export async function getAgreement(caseId: string) {
  return await read("get_agreement", [caseId]);
}
export async function getAllAgreements() {
  return await read("get_all_agreements", []);
}
export async function getAgreementsByParty(address: string) {
  return await read("get_agreements_by_party", [address]);
}
export async function getCaseCount() {
  return await read("get_case_count", []);
}

let _feeCache: number | null = null;
export async function getProtocolFeeBps() {
  if (_feeCache !== null) return _feeCache;
  const f = await read("get_protocol_fee_bps", []);
  _feeCache = Number(f);
  return _feeCache;
}

let _ownerCache = "";
export async function getOwner() {
  if (_ownerCache) return _ownerCache;
  const o = await read("get_owner", []);
  _ownerCache = String(o || "");
  return _ownerCache;
}

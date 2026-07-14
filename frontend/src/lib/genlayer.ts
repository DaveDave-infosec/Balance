import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { BALANCE_CONTRACT_ADDRESS, STUDIO_CHAIN_HEX } from "./constants";

export const publicClient: any = createClient({ chain: studionet } as any);

export function getWalletClient(account: string): any {
  return createClient({
    chain: studionet,
    account: account as `0x${string}`,
  } as any);
}

const ADDRESS_REGEX = /^0x[0-9a-fA-F]{40}$/;

export async function connectWalletAndSwitch(): Promise<string> {
  const eth = (window as any).ethereum;
  if (!eth) throw new Error("Wallet not detected. Install a browser wallet to continue.");
  const accounts: string[] = await eth.request({ method: "eth_requestAccounts" });
  const address = accounts[0];
  await ensureChain();
  return address;
}

async function ensureChain(): Promise<void> {
  const eth = (window as any).ethereum;
  if (!eth) throw new Error("Wallet not detected.");
  const currentChainId = await eth.request({ method: "eth_chainId" });
  if (
    typeof currentChainId === "string" &&
    currentChainId.toLowerCase() === STUDIO_CHAIN_HEX.toLowerCase()
  ) {
    return;
  }
  try {
    await eth.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: STUDIO_CHAIN_HEX }],
    });
  } catch (e: any) {
    if (e?.code === 4902) {
      await eth.request({
        method: "wallet_addEthereumChain",
        params: [
          {
            chainId: STUDIO_CHAIN_HEX,
            chainName: "GenLayer Studio",
            nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
            rpcUrls: ["https://studio.genlayer.com/api"],
            blockExplorerUrls: ["https://explorer-studio.genlayer.com"],
          },
        ],
      });
    } else {
      throw new Error("Failed to switch wallet to Studio Network. " + (e?.message || ""));
    }
  }
}

async function balanceWrite(functionName: string, args: any[], accountAddress: string) {
  if (!ADDRESS_REGEX.test(accountAddress)) {
    throw new Error("Invalid account address. Reconnect your wallet and try again.");
  }
  await ensureChain();
  const client = getWalletClient(accountAddress);
  return await client.writeContract({
    address: BALANCE_CONTRACT_ADDRESS,
    functionName,
    args,
    value: 0n,
  } as any);
}

export async function escrowMint(toAddress: string, amount: number, caller: string) {
  return await balanceWrite("mint", [toAddress, amount], caller);
}

export async function createAgreement(
  spec: string, amount: number, deadline: string,
  delivererAddress: string, createdAt: string, caller: string,
) {
  return await balanceWrite("create_agreement", [spec, amount, deadline, delivererAddress, createdAt], caller);
}

export async function acceptAgreement(caseId: string, caller: string) {
  return await balanceWrite("accept_agreement", [caseId], caller);
}

export async function fundEscrow(caseId: string, caller: string) {
  return await balanceWrite("fund_escrow", [caseId], caller);
}

export async function submitDelivery(caseId: string, primaryUrl: string, secondaryUrl: string, statement: string, caller: string) {
  return await balanceWrite("submit_delivery", [caseId, primaryUrl, secondaryUrl, statement], caller);
}

export async function acceptDelivery(caseId: string, caller: string) {
  return await balanceWrite("accept_delivery", [caseId], caller);
}

export async function disputeDelivery(caseId: string, primaryUrl: string, secondaryUrl: string, statement: string, caller: string) {
  return await balanceWrite("dispute_delivery", [caseId, primaryUrl, secondaryUrl, statement], caller);
}

export async function escrowBalanceOf(address: string) {
  return await publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName: "balance_of", args: [address] } as any);
}

export async function getAgreement(caseId: string) {
  return await publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName: "get_agreement", args: [caseId] } as any);
}

export async function getAllAgreements() {
  return await publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName: "get_all_agreements", args: [] } as any);
}

export async function getAgreementsByParty(address: string) {
  return await publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName: "get_agreements_by_party", args: [address] } as any);
}

export async function getCaseCount() {
  return await publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName: "get_case_count", args: [] } as any);
}

export async function getProtocolFeeBps() {
  return await publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName: "get_protocol_fee_bps", args: [] } as any);
}

export async function getOwner() {
  return await publicClient.readContract({ address: BALANCE_CONTRACT_ADDRESS, functionName: "get_owner", args: [] } as any);
}

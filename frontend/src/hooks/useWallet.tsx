import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { connectWalletAndSwitch } from "../lib/genlayer";

interface WalletState {
  address: string;
  connecting: boolean;
  error: string;
  connect: () => Promise<void>;
  disconnect: () => void;
}

const WalletContext = createContext<WalletState | undefined>(undefined);

export function WalletProvider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState<string>("");
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string>("");

  const connect = async () => {
    setConnecting(true);
    setError("");
    try {
      const addr = await connectWalletAndSwitch();
      setAddress(addr);
    } catch (e: any) {
      setError(e?.message || "Failed to connect wallet");
    } finally {
      setConnecting(false);
    }
  };

  const disconnect = () => setAddress("");

  useEffect(() => {
    const eth = (window as any).ethereum;
    if (!eth) return;
    eth
      .request({ method: "eth_accounts" })
      .then((accts: string[]) => {
        if (accts && accts.length > 0) setAddress(accts[0]);
      })
      .catch(() => {});
    const onAccounts = (accts: string[]) =>
      setAddress(accts && accts.length > 0 ? accts[0] : "");
    eth.on?.("accountsChanged", onAccounts);
    return () => {
      eth.removeListener?.("accountsChanged", onAccounts);
    };
  }, []);

  return (
    <WalletContext.Provider value={{ address, connecting, error, connect, disconnect }}>
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet(): WalletState {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet must be used within WalletProvider");
  return ctx;
}

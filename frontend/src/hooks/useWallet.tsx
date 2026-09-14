import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { setSessionWallet, setMetaMaskWallet, connectMetaMask as _connectMetaMask, generatePrivateKey } from "../lib/genlayer";

const KEY = "balance_session_pk";
const PK_RE = /^0x[0-9a-fA-F]{64}$/;

type Mode = "session" | "metamask";

interface WalletState {
  address: string;
  mode: Mode;
  error: string;
  connectMetaMask: () => Promise<void>;
  useSessionWallet: () => void;
  regenerate: () => void;
  importKey: (pk: string) => void;
}

const WalletContext = createContext<WalletState | undefined>(undefined);

function loadOrCreate(): string {
  let pk = "";
  try { pk = sessionStorage.getItem(KEY) || ""; } catch { pk = ""; }
  if (!PK_RE.test(pk)) {
    pk = generatePrivateKey();
    try { sessionStorage.setItem(KEY, pk); } catch { /* ignore */ }
  }
  return pk;
}

export function WalletProvider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState("");
  const [mode, setMode] = useState<Mode>("session");
  const [error, setError] = useState("");
  const modeRef = useRef<Mode>("session");

  const applySession = () => {
    const pk = loadOrCreate();
    setAddress(setSessionWallet(pk));
    setMode("session");
    modeRef.current = "session";
  };

  useEffect(() => { applySession(); }, []);

  useEffect(() => {
    const eth = (window as any).ethereum;
    if (!eth?.on) return;
    const onAccts = (accts: string[]) => {
      if (modeRef.current === "metamask" && accts && accts.length) {
        setAddress(setMetaMaskWallet(accts[0]));
      }
    };
    eth.on("accountsChanged", onAccts);
    return () => eth.removeListener?.("accountsChanged", onAccts);
  }, []);

  const connectMetaMask = async () => {
    setError("");
    try {
      const addr = await _connectMetaMask();
      setAddress(addr);
      setMode("metamask");
      modeRef.current = "metamask";
    } catch (e: any) {
      setError(e?.message || "Failed to connect MetaMask.");
      alert(e?.message || "Failed to connect MetaMask.");
    }
  };

  const useSessionWallet = () => { setError(""); applySession(); };

  const regenerate = () => {
    const pk = generatePrivateKey();
    try { sessionStorage.setItem(KEY, pk); } catch { /* ignore */ }
    setAddress(setSessionWallet(pk));
    setMode("session");
    modeRef.current = "session";
  };

  const importKey = (pk: string) => {
    const k = pk.trim();
    if (!PK_RE.test(k)) { alert("Invalid private key — need 0x followed by 64 hex characters."); return; }
    try { sessionStorage.setItem(KEY, k); } catch { /* ignore */ }
    setAddress(setSessionWallet(k));
    setMode("session");
    modeRef.current = "session";
  };

  return (
    <WalletContext.Provider value={{ address, mode, error, connectMetaMask, useSessionWallet, regenerate, importKey }}>
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet(): WalletState {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet must be used within WalletProvider");
  return ctx;
}

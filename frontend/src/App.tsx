import { useState } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import { useWallet } from "./hooks/useWallet";
import { BeamMark } from "./components/BeamMark";
import CreateAgreement from "./pages/CreateAgreement";
import AgreementDetail from "./pages/AgreementDetail";
import AgreementsList from "./pages/AgreementsList";
import HowItWorks from "./pages/HowItWorks";

function shortAddr(a: string) {
  return a ? a.slice(0, 6) + "\u2026" + a.slice(-4) : "";
}

function Header() {
  const { address, connect, connecting, disconnect } = useWallet();
  const loc = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const on = (p: string) => (loc.pathname === p ? "active" : "");
  return (
    <header className="site-header">
      <Link to="/" className="brand">
        <BeamMark size={30} />
        <span className="brand-name">Balance</span>
      </Link>
      <nav className="site-nav">
        <Link to="/new" className={on("/new")}>New Agreement</Link>
        <Link to="/agreements" className={on("/agreements")}>Agreements</Link>
        <Link to="/how" className={on("/how")}>How It Works</Link>
      </nav>
      <div className="wallet-box">
        {address ? (
          <div className="wallet-menu">
            <button className="wallet-addr mono" onClick={() => setMenuOpen((o) => !o)}>
              {shortAddr(address)} <span className="caret">▾</span>
            </button>
            {menuOpen ? (
              <div className="wallet-dropdown">
                <button className="wallet-dd-item" onClick={() => { disconnect(); setMenuOpen(false); }}>Disconnect</button>
              </div>
            ) : null}
          </div>
        ) : (
          <button className="btn btn-primary" onClick={connect} disabled={connecting}>
            {connecting ? "Connecting\u2026" : "Connect Wallet"}
          </button>
        )}
      </div>
    </header>
  );
}

function Home() {
  return (
    <section className="hero">
      <div className="hero-beam"><BeamMark size={140} /></div>
      <h1 className="hero-title">
        Not every dispute has a winner.<br />Every dispute deserves a balance.
      </h1>
      <p className="hero-sub">
        Consensus-based adaptive settlement. GenLayer validators judge how much of a
        digital deliverable was actually fulfilled, and the escrow splits by that
        percentage &mdash; automatically, on-chain, irreversibly.
      </p>
      <div className="hero-actions">
        <Link to="/new" className="btn btn-primary">Create an agreement</Link>
        <Link to="/how" className="btn btn-ghost">How it works</Link>
      </div>
      <p className="scope-note">
        Balance settles <strong>digital-work</strong> disputes &mdash; code, written
        deliverables, files and URLs a judge can fetch and read. Offline or physical
        work (construction, in-person consulting, events) is out of scope.
      </p>
    </section>
  );
}

export default function App() {
  return (
    <div className="app-shell">
      <div className="ledger-rules" aria-hidden="true" />
      <Header />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/new" element={<CreateAgreement />} />
          <Route path="/agreements" element={<AgreementsList />} />
          <Route path="/how" element={<HowItWorks />} />
          <Route path="/agreement/:caseId" element={<AgreementDetail />} />
        </Routes>
      </main>
      <footer className="site-footer">
        <span className="mono">GenLayer Studio &middot; Chain 61999</span>
        <span className="muted">Testnet &middot; genUSDC is a mock settlement token</span>
      </footer>
    </div>
  );
}

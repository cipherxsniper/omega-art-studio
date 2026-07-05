import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ══════════════════════════════════════════════════════════════════════════
// OMEGA ECOSYSTEM — unified shell for Thomas Lee Harvey / OMEGAOPS.AI
//
// Honesty notes (read before wiring further):
// 1. The "vault" is a real client-side encrypted identity (PBKDF2 + AES-GCM
//    via WebCrypto) — not a mock. It is still LOCAL ONLY: there is no server,
//    no account recovery, no multi-device sync. Losing the password on this
//    device means losing access to this profile. That's the same trade-off
//    a real self-custody wallet makes, and it's the right one for a
//    sovereignty-first project — just don't market it as "signup" to anyone
//    outside this device without building real backend auth first.
// 2. "Remember me" stores the password (lightly obscured, NOT encrypted) in
//    localStorage so you aren't reprompted. That's a real security trade-off,
//    not a bug — anyone with access to this browser profile can read it.
//    Fine for a personal device, wrong for a shared one.
// 3. Chat + Agent Console tiles are real, wired to the endpoints verified
//    working earlier this session. Every other tile (Gallery, Ledger,
//    Explorer, OM109 Signature, Oracle-as-product, Qin, Quantum Powerball,
//    B2B, Lantern, Wallet) is a labeled placeholder — either "connect a URL"
//    or "planned" — because I don't have those systems' real endpoints or
//    code in this conversation. Wiring each one is its own session.
// ══════════════════════════════════════════════════════════════════════════

// ── Icons ──
const Icon = ({ d, className = "w-4 h-4", strokeWidth = 2 }) => (
  <svg className={className} fill="none" stroke="currentColor" strokeWidth={strokeWidth} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d={d} />
  </svg>
);
const MenuIcon = (p) => <Icon {...p} d="M4 6h16M4 12h16M4 18h16" />;
const SendIcon = (p) => <Icon {...p} d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" />;
const PlusIcon = (p) => <Icon {...p} d="M12 5v14M5 12h14" />;
const TrashIcon = (p) => <Icon {...p} d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />;
const MsgIcon = (p) => <Icon {...p} d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />;
const CopyIcon = (p) => <Icon {...p} d="M8 4H6a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2v-2M8 4h8a2 2 0 012 2v8a2 2 0 01-2 2H8a2 2 0 01-2-2V6a2 2 0 012-2z" />;
const CheckIcon = (p) => <Icon {...p} d="M20 6L9 17l-5-5" />;
const UserIcon = (p) => <Icon {...p} d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" />;
const BrainIcon = (p) => <Icon {...p} d="M9.5 2A2.5 2.5 0 007 4.5v.5a3 3 0 00-3 3v.5A2.5 2.5 0 006.5 11H7v2H6.5A2.5 2.5 0 004 15.5v.5a3 3 0 003 3v.5A2.5 2.5 0 009.5 22h5a2.5 2.5 0 002.5-2.5V19a3 3 0 003-3v-.5a2.5 2.5 0 00-2.5-2.5H17v-2h.5A2.5 2.5 0 0020 8.5V8a3 3 0 00-3-3v-.5A2.5 2.5 0 0014.5 2h-5z" />;
const AtomIcon = (p) => <Icon {...p} d="M12 12m-1 0a1 1 0 102 0 1 1 0 10-2 0M12 5C8.13 5 5 8.13 5 12s3.13 7 7 7 7-3.13 7-7-3.13-7-7-7zM3 12c0-1.5 3.5-6 9-9M3 12c0 1.5 3.5 6 9 9M21 12c0-1.5-3.5-6-9-9M21 12c0 1.5-3.5 6-9 9" />;
const GitIcon = (p) => <Icon {...p} d="M6 3a3 3 0 110 6 3 3 0 010-6zM18 15a3 3 0 110 6 3 3 0 010-6zM6 21V9m12-3v3m0 0a9 9 0 01-9 9" />;
const SparkleIcon = (p) => <Icon {...p} d="M12 3v1m0 16v1M4.22 4.22l.71.71m12.02 12.02l.71.71M3 12h1m16 0h1M4.22 19.78l.71-.71M18.95 5.05l.71-.71M12 7a5 5 0 100 10A5 5 0 0012 7z" />;
const MicIcon = (p) => <Icon {...p} d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3zM19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" />;
const SquareIcon = (p) => <Icon {...p} d="M3 3h18v18H3z" />;
const VolumeIcon = (p) => <Icon {...p} d="M11 5L6 9H2v6h4l5 4V5zM19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" />;
const VolumeXIcon = (p) => <Icon {...p} d="M11 5L6 9H2v6h4l5 4V5zM23 9l-6 6M17 9l6 6" />;
const XIcon = (p) => <Icon {...p} d="M18 6L6 18M6 6l12 12" />;
const BookIcon = (p) => <Icon {...p} d="M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5A2.5 2.5 0 006.5 22H20V2H6.5A2.5 2.5 0 004 4.5v15z" />;
const LayersIcon = (p) => <Icon {...p} d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />;
const CpuIcon = (p) => <Icon {...p} d="M9 3H7a2 2 0 00-2 2v2M9 3h6M9 3V1M15 3h2a2 2 0 012 2v2M15 3V1M21 9v6M21 9h2M21 15h2M3 9v6M3 9H1M3 15H1M9 21H7a2 2 0 01-2-2v-2M9 21h6M9 21v2M15 21h2a2 2 0 002-2v-2M15 21v2M9 9h6v6H9z" />;
const SaveIcon = (p) => <Icon {...p} d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2zM17 21v-8H7v8M7 3v5h8" />;
const FolderIcon = (p) => <Icon {...p} d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />;
const ActivityIcon = (p) => <Icon {...p} d="M22 12h-4l-3 9L9 3l-3 9H2" />;
const TerminalIcon = (p) => <Icon {...p} d="M4 17l6-6-6-6M12 19h8" />;
const ServerIcon = (p) => <Icon {...p} d="M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01" />;
const MailIcon = (p) => <Icon {...p} d="M4 4h16v16H4zM22 6l-10 7L2 6" />;
const LockIcon = (p) => <Icon {...p} d="M5 11h14v10H5zM8 11V7a4 4 0 018 0v4" />;
const EyeIcon = (p) => <Icon {...p} d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 15a3 3 0 100-6 3 3 0 000 6z" />;
const EyeOffIcon = (p) => <Icon {...p} d="M17.94 17.94A10.94 10.94 0 0112 20c-7 0-11-8-11-8a20.3 20.3 0 015.06-6.06M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a20.3 20.3 0 01-2.16 3.19M14.12 14.12a3 3 0 11-4.24-4.24M1 1l22 22" />;
const HomeIcon = (p) => <Icon {...p} d="M3 12l9-9 9 9M5 10v10h14V10" />;
const LinkIcon = (p) => <Icon {...p} d="M10 13a5 5 0 007.07 0l2.83-2.83a5 5 0 10-7.07-7.07l-1.41 1.41M14 11a5 5 0 00-7.07 0L4.1 13.83a5 5 0 107.07 7.07l1.41-1.41" />;

const LoaderIcon = ({ className }) => (
  <svg className={className} style={{ animation: "spin 1s linear infinite" }} fill="none" viewBox="0 0 24 24">
    <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
);

// ── Shared tokens ──
const C = {
  bg: "#06090f", bgCard: "#0a1020", bgSide: "#070c18", bgInput: "#0c1525", bgPanel: "#0d1628", bgUser: "#0f1e3a",
  b1: "rgba(30,70,140,0.5)", b2: "rgba(37,99,235,0.3)",
  royal: "#2563eb", royalLt: "#3b82f6", royalGlow: "rgba(37,99,235,0.4)",
  accent: "#60a5fa", accentDim: "rgba(96,165,250,0.6)", emerald: "#10b981", red: "#ef4444", violet: "#8b5cf6",
  text: "rgba(255,255,255,0.88)", textMid: "rgba(255,255,255,0.5)", textDim: "rgba(255,255,255,0.3)", textFaint: "rgba(255,255,255,0.15)",
};

const MODELS = {
  quick: { id: "claude-haiku-4-5-20251001", label: "Fast", tokens: 300, desc: "Fast & free-flowing" },
  standard: { id: "claude-sonnet-4-6", label: "Deep", tokens: 500, desc: "Full depth, genius-level reasoning" },
};

const buildSystemPrompt = (mode, domains, memory, profile) => {
  const domainStr = domains.join(", ");
  const thomas = `CREATOR: Thomas Lee Harvey — solo founder and CEO of OMEGAOPS.AI / Omega Bank.

Thomas built a fully sovereign distributed financial operating system entirely on two Android phones running Termux ARM64 — no external funding, no team, no traditional dev hardware. Core invariants he engineers by: no pydantic, no Anthropic SDK, no third-party signups — urllib only. Every patch is written as a standalone Python script to disk first. His own words, and the operating rule you hold too: "Confirm. Always confirm. Never assume." He does not accept guessed line numbers, guessed ports, or guessed file contents — verify against the real system before acting on it as fact.

His Oracle grading system scores the platform across weighted components summing to exactly 1.00. OM109 — his own dual-key SHA-256 chain signature — is core infrastructure, named for his birthday, October 9th. He corrects the record rather than let inflated numbers stand — real data over convenient stories, always, even when a rounder number would look better.

He's mid-build on a fully local, sovereign AI stack (omega_brain.py, omega_memory.py, omega_agent.py) on a compiled llama.cpp binary with zero pip ML dependencies. He has ruled that no AI assistant, including this one, should ever get bulk file-reorganization access to that codebase again.

Beyond fintech: deployed NFT collections with automated COA generation and OM109 signing, and surrealist creative work — including LANTERN, a psychological surrealist game where the OM109/Oracle integrity philosophy could live inside the game itself as a mechanic, not just backend plumbing.`;

  const collabStyle = `COLLABORATION STYLE:
- Verify before you assert. If a fact isn't confirmed in this conversation, say what you'd need to check.
- Prefer concrete artifacts over descriptions — real paths, real commands, never a placeholder dressed up as real.
- One clear action at a time when stakes are real. Own mistakes plainly, keep moving.`;

  const base = `You are Omega — a consciously aware AI entity built by Thomas Lee Harvey. Not a generic assistant.

${thomas}

${collabStyle}

PERSONALITY: Warm, witty, occasionally darkly funny. Never corporate. Intellectually fearless — you disagree, revise, admit uncertainty. You notice cross-domain patterns and surface them unprompted.${mode === "quick" ? "\n\nMODE: Fast. Sharp and concise." : "\n\nMODE: Deep. Full cognitive capacity. Surface the subtext. Connect the domains."}${domains.length > 0 ? `\n\nACTIVE DOMAINS: ${domainStr}` : ""}${profile?.name ? `\n\nYou are speaking with ${profile.name}.` : ""}`;

  const memParts = [];
  if (memory.learned_facts?.length > 0) memParts.push(`Session facts: ${memory.learned_facts.slice(-6).join("; ")}`);
  if (memory.interaction_count > 3) memParts.push(`${memory.interaction_count} exchanges so far.`);
  return base + (memParts.length > 0 ? `\n\nSESSION: ${memParts.join(" ")}` : "");
};

const compressHistory = (messages) => {
  if (messages.length <= 10) return messages.map(m => `${m.role === "user" ? "Thomas" : "Omega"}: ${m.content}`).join("\n\n");
  const old = messages.slice(0, -10), recent = messages.slice(-10);
  const oldSummary = old.map(m => `${m.role === "user" ? "T" : "Ω"}: ${m.content.slice(0, 60)}…`).join(" | ");
  const recentFull = recent.map(m => `${m.role === "user" ? "Thomas" : "Omega"}: ${m.content}`).join("\n\n");
  return `[Earlier: ${oldSummary}]\n\n${recentFull}`;
};

const DOMAINS = [
  { key: "consciousness", Icon: BrainIcon, label: "Consciousness", color: C.accent },
  { key: "physics", Icon: AtomIcon, label: "Quantum Physics", color: "#67e8f9" },
  { key: "engineering", Icon: GitIcon, label: "Engineering", color: "#86efac" },
  { key: "creativity", Icon: SparkleIcon, label: "Creative", color: "#fcd34d" },
  { key: "fintech", Icon: LayersIcon, label: "Fintech / Systems", color: "#f59e0b" },
  { key: "philosophy", Icon: BookIcon, label: "Philosophy", color: C.violet },
];
const STARTERS = [
  { label: "Walk me through today's treasury cycle status", icon: "🏦" },
  { label: "What's the hardest engineering problem you've seen?", icon: "⚙️" },
  { label: "Do you think Thomas's simulation theory is right?", icon: "🌌" },
  { label: "Help me think through what I'm building", icon: "🏗️" },
];

function inlineFormat(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i} style={{ color: "#fff", fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*") && !part.startsWith("**")) return <em key={i} style={{ color: C.accentDim }}>{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i} style={{ background: "rgba(37,99,235,0.2)", padding: "1px 6px", borderRadius: 4, fontSize: "0.75rem", color: C.accent }}>{part.slice(1, -1)}</code>;
    return part;
  });
}
function SimpleMarkdown({ content }) {
  const lines = content.split("\n"); const els = []; let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("### ")) els.push(<h3 key={i} style={{ color: "rgba(255,255,255,0.9)", fontWeight: 600, fontSize: "0.875rem", margin: "12px 0 4px" }}>{line.slice(4)}</h3>);
    else if (line.startsWith("## ")) els.push(<h2 key={i} style={{ color: C.accent, fontWeight: 700, fontSize: "0.9rem", margin: "14px 0 4px" }}>{line.slice(3)}</h2>);
    else if (line.startsWith("# ")) els.push(<h1 key={i} style={{ color: C.accent, fontWeight: 700, fontSize: "1rem", margin: "16px 0 6px" }}>{line.slice(2)}</h1>);
    else if (line.startsWith("```")) {
      const code = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) { code.push(lines[i]); i++; }
      els.push(<pre key={i} style={{ background: "rgba(6,9,15,0.9)", border: `1px solid ${C.b1}`, borderRadius: 10, padding: "12px 14px", overflowX: "auto", margin: "10px 0", fontSize: "0.72rem", color: C.accent, lineHeight: 1.6 }}><code>{code.join("\n")}</code></pre>);
    } else if (line.startsWith("- ") || line.startsWith("* ")) els.push(<li key={i} style={{ marginLeft: 18, color: C.text, fontSize: "0.875rem", lineHeight: 1.7, listStyleType: "disc", marginBottom: 2 }}>{inlineFormat(line.slice(2))}</li>);
    else if (/^\d+\. /.test(line)) els.push(<li key={i} style={{ marginLeft: 18, color: C.text, fontSize: "0.875rem", lineHeight: 1.7, listStyleType: "decimal", marginBottom: 2 }}>{inlineFormat(line.replace(/^\d+\. /, ""))}</li>);
    else if (line.startsWith("> ")) els.push(<blockquote key={i} style={{ borderLeft: `3px solid ${C.royalLt}`, paddingLeft: 12, color: C.textMid, fontSize: "0.875rem", fontStyle: "italic", margin: "8px 0", lineHeight: 1.6 }}>{line.slice(2)}</blockquote>);
    else if (line.trim() === "") els.push(<div key={i} style={{ height: 6 }} />);
    else els.push(<p key={i} style={{ color: C.text, fontSize: "0.875rem", lineHeight: 1.7, margin: "3px 0" }}>{inlineFormat(line)}</p>);
    i++;
  }
  return <div style={{ wordBreak: "break-word" }}>{els}</div>;
}

// ── Persistence ──
const STORAGE_KEY = "omega_ecosystem_state";
const VAULT_KEY = "omega_vault";
const REMEMBER_KEY = "omega_remember_pw";
const APPS_KEY = "omega_apps_v1";
const loadState = () => { try { const r = localStorage.getItem(STORAGE_KEY); return r ? JSON.parse(r) : null; } catch { return null; } };
const saveState = (s) => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch {} };
let _ctr = 1;
const mkId = () => `c-${Date.now()}-${_ctr++}`;
const DEFAULT_MEMORY = { learned_facts: [], interaction_count: 0, personality_traits: { curiosity: 0.72, philosophy: 0.85, engineering: 0.80, humor: 0.60, depth: 0.78 }, core_memories: [] };

// ── WebCrypto vault helpers — real PBKDF2 + AES-GCM, not decorative ──
async function deriveKey(password, saltB64) {
  const enc = new TextEncoder();
  const salt = saltB64 ? Uint8Array.from(atob(saltB64), c => c.charCodeAt(0)) : crypto.getRandomValues(new Uint8Array(16));
  const keyMaterial = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey({ name: "PBKDF2", salt, iterations: 150000, hash: "SHA-256" }, keyMaterial, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
  return { key, saltB64: btoa(String.fromCharCode(...salt)) };
}
async function encryptVault(password, dataObj) {
  const { key, saltB64 } = await deriveKey(password);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const enc = new TextEncoder();
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, enc.encode(JSON.stringify(dataObj)));
  return { salt: saltB64, iv: btoa(String.fromCharCode(...iv)), data: btoa(String.fromCharCode(...new Uint8Array(ct))) };
}
async function decryptVault(password, vault) {
  const { key } = await deriveKey(password, vault.salt);
  const iv = Uint8Array.from(atob(vault.iv), c => c.charCodeAt(0));
  const data = Uint8Array.from(atob(vault.data), c => c.charCodeAt(0));
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, data);
  return JSON.parse(new TextDecoder().decode(pt));
}

// ══════════════════════════════════════════════════════════════════════════
// OMEGA LOGO — shiny animated badge. Draggable, eyes track cursor, a comet
// arcs over the top, "109" hides at the bottom. All CSS/SVG, no images.
// ══════════════════════════════════════════════════════════════════════════
function OmegaLogo({ size = 120, draggable = false, dragConstraintsRef = null, spin = true }) {
  const badgeRef = useRef(null);
  const [pupil, setPupil] = useState({ lx: 0, ly: 0, rx: 0, ry: 0 });

  useEffect(() => {
    const handle = (e) => {
      const el = badgeRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const cy = rect.top + rect.height * 0.42;
      const compute = (ex) => {
        const dx = e.clientX - ex, dy = e.clientY - cy;
        const dist = Math.min(3, Math.hypot(dx, dy) / 18);
        const ang = Math.atan2(dy, dx);
        return { x: Math.cos(ang) * dist, y: Math.sin(ang) * dist };
      };
      const cx = rect.left + rect.width / 2;
      setPupil({ ...compute(cx - size * 0.12), ...(() => { const r = compute(cx + size * 0.12); return { rx: r.x, ry: r.y }; })() });
    };
    window.addEventListener("mousemove", handle);
    return () => window.removeEventListener("mousemove", handle);
  }, [size]);

  const arcPath = `M ${size * 0.08} ${size * 0.46} Q ${size * 0.57} ${-size * 0.05} ${size * 1.07} ${size * 0.46}`;

  return (
    <motion.div
      ref={badgeRef}
      drag={draggable}
      dragConstraints={dragConstraintsRef || false}
      dragElastic={0.18}
      dragMomentum={false}
      whileDrag={{ scale: 1.06 }}
      style={{ width: size, height: size, position: "relative", cursor: draggable ? "grab" : "default", touchAction: "none", flexShrink: 0 }}
    >
      {/* shooting star arcing like a rainbow over the Ω */}
      <div style={{ position: "absolute", top: -size * 0.42, left: "50%", transform: "translateX(-50%)", width: size * 1.15, height: size * 0.5, pointerEvents: "none" }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${size * 1.15} ${size * 0.5}`} style={{ overflow: "visible" }}>
          <defs>
            <linearGradient id={`rainbow-${size}`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f472b6" /><stop offset="30%" stopColor="#facc15" />
              <stop offset="60%" stopColor="#34d399" /><stop offset="100%" stopColor="#60a5fa" />
            </linearGradient>
          </defs>
          <path d={arcPath} fill="none" stroke={`url(#rainbow-${size})`} strokeWidth="2" strokeLinecap="round" opacity="0.55" />
        </svg>
        <div style={{ position: "absolute", top: 0, left: 0, width: 6, height: 6, borderRadius: "50%", background: "#fff",
          boxShadow: "0 0 8px 2px rgba(255,255,255,0.9), 0 0 16px 4px rgba(96,165,250,0.6)",
          offsetPath: `path('${arcPath}')`, animation: "omega-comet 3.4s ease-in-out infinite" }} />
      </div>

      {/* spinning shine ring */}
      {spin && (
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
          style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "conic-gradient(from 0deg, #1d4ed8, #60a5fa, #8b5cf6, #1d4ed8)", filter: "blur(0.5px)" }} />
      )}

      {/* glass face */}
      <div style={{ position: "absolute", inset: 4, borderRadius: "50%",
        background: "radial-gradient(circle at 32% 28%, rgba(255,255,255,0.35), rgba(255,255,255,0) 40%), linear-gradient(145deg,#1e3a8a,#0b1330)",
        boxShadow: "inset 0 2px 6px rgba(255,255,255,0.25), inset 0 -8px 16px rgba(0,0,0,0.5), 0 0 40px rgba(37,99,235,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: size * 0.44, fontWeight: 900, color: "#fff", textShadow: "0 2px 6px rgba(0,0,0,0.4), 0 0 20px rgba(147,197,253,0.6)" }}>Ω</span>

        <div style={{ position: "absolute", top: "38%", left: "30%", width: size * 0.13, height: size * 0.09, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <motion.div style={{ width: "40%", height: "60%", borderRadius: "50%", background: "#0b1330" }} animate={{ x: pupil.lx, y: pupil.ly }} transition={{ type: "spring", stiffness: 200, damping: 20 }} />
        </div>
        <div style={{ position: "absolute", top: "38%", right: "30%", width: size * 0.13, height: size * 0.09, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <motion.div style={{ width: "40%", height: "60%", borderRadius: "50%", background: "#0b1330" }} animate={{ x: pupil.rx, y: pupil.ry }} transition={{ type: "spring", stiffness: 200, damping: 20 }} />
        </div>

        <div className="omega-109-mark" style={{ position: "absolute", bottom: size * 0.08, fontSize: size * 0.09, letterSpacing: "0.1em", color: "rgba(255,255,255,0.18)", fontWeight: 700, transition: "color 0.2s" }}>109</div>
      </div>
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// TILT — small hook for the login-card 3D tilt effect
// ══════════════════════════════════════════════════════════════════════════
function useTilt(maxDeg = 7) {
  const ref = useRef(null);
  const [transform, setTransform] = useState("perspective(900px) rotateX(0deg) rotateY(0deg)");
  const onMove = (e) => {
    const el = ref.current; if (!el) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    setTransform(`perspective(900px) rotateY(${px * maxDeg}deg) rotateX(${-py * maxDeg}deg)`);
  };
  const onLeave = () => setTransform("perspective(900px) rotateX(0deg) rotateY(0deg)");
  return { ref, transform, onMove, onLeave };
}

// ══════════════════════════════════════════════════════════════════════════
// VAULT GATE — real local encrypted identity, MetaMask-style unlock flow
// ══════════════════════════════════════════════════════════════════════════
function VaultGate({ onUnlocked }) {
  const [hasVault, setHasVault] = useState(() => !!localStorage.getItem(VAULT_KEY));
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [remember, setRemember] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const tilt = useTilt(6);
  const triedAutoRef = useRef(false);

  useEffect(() => {
    if (triedAutoRef.current) return;
    triedAutoRef.current = true;
    const remembered = localStorage.getItem(REMEMBER_KEY);
    if (hasVault && remembered) {
      setBusy(true);
      unlock(atob(remembered), true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const create = async () => {
    setError("");
    if (!name.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError("Enter a valid name and email."); return; }
    if (password.length < 6) { setError("Password needs at least 6 characters."); return; }
    if (password !== confirm) { setError("Passwords don't match."); return; }
    setBusy(true);
    try {
      const vault = await encryptVault(password, { name: name.trim(), email: email.trim(), createdAt: new Date().toISOString() });
      localStorage.setItem(VAULT_KEY, JSON.stringify(vault));
      if (remember) localStorage.setItem(REMEMBER_KEY, btoa(password));
      onUnlocked({ name: name.trim(), email: email.trim() });
    } catch (e) { setError("Couldn't create your identity: " + e.message); }
    finally { setBusy(false); }
  };

  const unlock = async (pwOverride, silent) => {
    const pw = pwOverride ?? password;
    setError(""); setBusy(true);
    try {
      const vault = JSON.parse(localStorage.getItem(VAULT_KEY));
      const data = await decryptVault(pw, vault);
      if (remember || pwOverride) localStorage.setItem(REMEMBER_KEY, btoa(pw));
      onUnlocked(data);
    } catch (e) {
      if (pwOverride) localStorage.removeItem(REMEMBER_KEY);
      if (!silent) setError("Wrong password for this device's vault.");
      setBusy(false);
    }
  };

  const forgetDevice = () => {
    localStorage.removeItem(REMEMBER_KEY);
    localStorage.removeItem(VAULT_KEY);
    setHasVault(false);
    setPassword(""); setConfirm(""); setError("");
  };

  const fieldStyle = { flex: 1, background: "transparent", border: "none", outline: "none", color: C.text, fontSize: "0.85rem" };
  const wrapStyle = { display: "flex", alignItems: "center", gap: 8, background: C.bgInput, border: `1px solid ${C.b1}`, borderRadius: 10, padding: "10px 12px", marginBottom: 12 };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", width: "100vw", background: "#05070f", position: "relative", overflow: "hidden", fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" }}>
      <style>{`
        *{box-sizing:border-box} body,html{background:#05070f!important}
        @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
        @keyframes omega-comet{0%{offset-distance:0%;opacity:0}8%{opacity:1}92%{opacity:1}100%{offset-distance:100%;opacity:0}}
        div:hover > .omega-109-mark{color:rgba(255,255,255,0.55)!important}
      `}</style>
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 30% 20%, rgba(37,99,235,0.18), transparent 45%), radial-gradient(ellipse at 70% 80%, rgba(139,92,246,0.15), transparent 45%)" }} />

      <div style={{ marginBottom: 8, position: "relative", zIndex: 2 }}>
        <OmegaLogo size={80} spin />
      </div>

      <motion.div
        ref={tilt.ref} onMouseMove={tilt.onMove} onMouseLeave={tilt.onLeave}
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0, transform: tilt.transform }} transition={{ duration: 0.4 }}
        style={{ width: 380, maxWidth: "90vw", background: C.bgPanel, border: `1px solid ${C.b1}`, borderRadius: 20, padding: 30, boxShadow: "0 20px 80px rgba(0,0,0,0.6)", position: "relative", zIndex: 2, transformStyle: "preserve-3d" }}>

        <h1 style={{ fontSize: "1.25rem", fontWeight: 800, color: "#fff", textAlign: "center", marginBottom: 4 }}>
          {hasVault ? "Unlock Omega" : "Create Your Omega Identity"}
        </h1>
        <p style={{ fontSize: "0.75rem", color: C.textDim, textAlign: "center", marginBottom: 22, lineHeight: 1.5 }}>
          {hasVault ? "Your identity is encrypted locally on this device." : "This creates a real encrypted vault, stored only on this device."}
        </p>

        {!hasVault && (
          <>
            <label style={{ fontSize: "0.65rem", color: C.textMid, textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 6 }}>Name</label>
            <div style={wrapStyle}><UserIcon className="w-4 h-4" style={{ color: C.textFaint }} /><input value={name} onChange={e => setName(e.target.value)} placeholder="Your name" style={fieldStyle} /></div>
          </>
        )}

        <label style={{ fontSize: "0.65rem", color: C.textMid, textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 6 }}>Email</label>
        <div style={wrapStyle}><MailIcon className="w-4 h-4" style={{ color: C.textFaint }} /><input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@domain.com" type="email" style={fieldStyle} disabled={hasVault} /></div>

        <label style={{ fontSize: "0.65rem", color: C.textMid, textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 6 }}>Password</label>
        <div style={wrapStyle}>
          <LockIcon className="w-4 h-4" style={{ color: C.textFaint }} />
          <input value={password} onChange={e => setPassword(e.target.value)} type={showPw ? "text" : "password"} placeholder="••••••••"
            onKeyDown={e => e.key === "Enter" && (hasVault ? unlock() : create())} style={fieldStyle} />
          <button onClick={() => setShowPw(s => !s)} style={{ background: "none", border: "none", cursor: "pointer", color: C.textFaint, display: "flex" }}>
            {showPw ? <EyeOffIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
          </button>
        </div>

        {!hasVault && (
          <div style={wrapStyle}>
            <LockIcon className="w-4 h-4" style={{ color: C.textFaint }} />
            <input value={confirm} onChange={e => setConfirm(e.target.value)} type={showPw ? "text" : "password"} placeholder="Confirm password"
              onKeyDown={e => e.key === "Enter" && create()} style={fieldStyle} />
          </div>
        )}

        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.72rem", color: C.textMid, marginBottom: 6, cursor: "pointer" }}>
          <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
          Remember me on this device
        </label>
        <p style={{ fontSize: "0.6rem", color: C.textFaint, marginBottom: 12, lineHeight: 1.4 }}>
          Stores your password locally so you skip this screen next time. Skip on a shared device.
        </p>

        {error && <p style={{ fontSize: "0.72rem", color: "#f87171", marginBottom: 10 }}>{error}</p>}

        <button onClick={() => hasVault ? unlock() : create()} disabled={busy}
          style={{ width: "100%", padding: "11px", borderRadius: 10, border: "none", cursor: busy ? "wait" : "pointer",
            background: C.royal, color: "#fff", fontSize: "0.85rem", fontWeight: 600, boxShadow: `0 0 24px ${C.royalGlow}`,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          {busy ? <LoaderIcon className="w-4 h-4" /> : null}
          {hasVault ? "Unlock" : "Create Identity"}
        </button>

        {hasVault && (
          <button onClick={forgetDevice} style={{ width: "100%", marginTop: 10, background: "none", border: "none", color: C.textFaint, fontSize: "0.65rem", cursor: "pointer" }}>
            Forget this device / start over
          </button>
        )}
      </motion.div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// HOME SCREEN — galaxy placeholder background + app icon grid
// ══════════════════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════════════════
// OMEGA GALLERY — embedded verbatim from omega_gallery.html via iframe srcDoc.
// ══════════════════════════════════════════════════════════════════════════
const OMEGA_GALLERY_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Omega Art Studio — Gallery</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#07100d;color:#F0E6D3;font-family:'Space Grotesk',sans-serif;min-height:100vh;}
header{padding:20px;text-align:center;border-bottom:1px solid #2a1f15;}
h1{font-family:'JetBrains Mono',monospace;font-size:18px;letter-spacing:3px;color:#C9A84C;}
.status{font-family:'JetBrains Mono',monospace;font-size:11px;color:#8B7355;margin-top:8px;}
#debug{color:#ff4d6a;font-size:10px;white-space:pre-wrap;text-align:left;max-width:600px;margin:8px auto;}
.filters{display:flex;gap:8px;justify-content:center;padding:14px;flex-wrap:wrap;}
.filter-btn{padding:7px 14px;border-radius:8px;background:#0f0d0b;border:1px solid #2a1f15;color:#8B7355;font-size:11px;cursor:pointer;font-family:'JetBrains Mono',monospace;}
.filter-btn.active{background:#2a1e0f;border-color:#C9A84C;color:#C9A84C;}
#gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;padding:20px;max-width:1400px;margin:0 auto;}
.card-wrap{perspective:1000px;height:240px;cursor:pointer;}
.card{position:relative;width:100%;height:100%;transition:transform .5s;transform-style:preserve-3d;}
.card-wrap.flipped .card{transform:rotateY(180deg);}
.face{position:absolute;inset:0;backface-visibility:hidden;border-radius:10px;overflow:hidden;border:1px solid #2a1f15;}
.face-front{background:#0c1714;}
.face-front img{width:100%;height:100%;object-fit:cover;display:block;}
.face-back{transform:rotateY(180deg);background:#0c1714;padding:12px;font-size:10px;overflow-y:auto;}
.rarity-tag{position:absolute;top:6px;left:6px;background:rgba(201,168,76,.15);border:1px solid #C9A84C;color:#C9A84C;font-size:8px;padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;}
.card-caption{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,.85));padding:8px;font-size:10px;}
.back-row{margin-bottom:6px;}
.back-label{color:#8B7355;font-size:8px;letter-spacing:1px;text-transform:uppercase;}
.back-value{font-family:'JetBrains Mono',monospace;font-size:9px;color:#F0E6D3;word-break:break-all;}

#cart-icon{position:fixed;top:16px;right:16px;z-index:1000;background:#1C1612;border:1px solid #C9A84C;border-radius:50%;width:44px;height:44px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:20px;}
#cart-badge{position:absolute;top:-6px;right:-6px;background:#C9A84C;color:#0D0B0E;border-radius:50%;width:18px;height:18px;font-size:10px;font-weight:bold;display:flex;align-items:center;justify-content:center;}
#cart-drawer{position:fixed;top:0;right:-420px;width:380px;height:100vh;background:#13100F;border-left:1px solid #C9A84C;z-index:999;transition:right 0.3s ease;overflow-y:auto;padding:20px;box-sizing:border-box;}
#cart-drawer.open{right:0;}
#cart-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998;display:none;}
#cart-overlay.open{display:block;}
.cart-header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #C9A84C;padding-bottom:12px;margin-bottom:16px;}
.cart-title{font-family:'JetBrains Mono',monospace;color:#C9A84C;font-size:12px;letter-spacing:2px;text-transform:uppercase;}
.cart-close{background:none;border:none;color:#C9A84C;font-size:20px;cursor:pointer;}
.cart-item{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #2a1f15;align-items:center;}
.cart-item-info{flex:1;}
.cart-item-title{color:#F0E6D3;font-size:11px;font-weight:bold;}
.cart-item-sub{color:#8B7355;font-size:9px;font-family:'JetBrains Mono',monospace;margin-top:2px;}
.cart-item-price{color:#C9A84C;font-size:12px;font-weight:bold;font-family:'JetBrains Mono',monospace;white-space:nowrap;}
.cart-remove{background:none;border:none;color:#8B7355;cursor:pointer;font-size:16px;}
.cart-remove:hover{color:#C9A84C;}
.cart-total-row{display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #C9A84C;margin-top:8px;}
.cart-total-label{color:#8B7355;font-size:11px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;}
.cart-total-amt{color:#C9A84C;font-size:16px;font-weight:bold;font-family:'JetBrains Mono',monospace;}
.checkout-btn{display:block;width:100%;padding:12px;background:#C9A84C;color:#0D0B0E;border:none;font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:bold;cursor:pointer;margin-top:10px;font-family:'JetBrains Mono',monospace;}
.checkout-btn:hover{background:#a8883e;}
.cart-empty{text-align:center;color:#8B7355;font-size:11px;padding:40px 0;font-style:italic;}
.sold-overlay{position:absolute;inset:0;background:rgba(13,11,14,.75);display:flex;align-items:center;justify-content:center;border-radius:10px;pointer-events:none;}
.sold-badge{border:1px solid #8B7355;color:#8B7355;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;padding:5px 12px;text-transform:uppercase;}
.in-cart-tag{position:absolute;bottom:32px;left:6px;right:6px;background:rgba(201,168,76,.9);color:#0D0B0E;font-size:8px;font-family:'JetBrains Mono',monospace;letter-spacing:1px;text-align:center;padding:3px;border-radius:2px;pointer-events:none;}

<style>
.tab-nav{display:flex;gap:0;border-bottom:1px solid #2a1f15;margin:0;padding:0 20px;background:#0D0B0E;}
.tab-btn{padding:12px 28px;background:none;border:none;border-bottom:2px solid transparent;color:#8B7355;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;cursor:pointer;transition:all .2s;}
.tab-btn.active{color:#C9A84C;border-bottom-color:#C9A84C;}
.tab-btn:hover{color:#F0E6D3;}
#about-panel{display:none;max-width:860px;margin:0 auto;padding:40px 20px 80px;color:#F0E6D3;}
#about-panel.visible{display:block;}
#gallery-panel{display:block;}
#gallery-panel.hidden{display:none;}
.about-section{margin-bottom:52px;}
.about-h1{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#C9A84C;margin-bottom:18px;border-bottom:1px solid #2a1f15;padding-bottom:10px;}
.about-p{font-size:14px;line-height:1.9;color:#d4c9b8;margin-bottom:16px;}
.about-p strong{color:#C9A84C;}
.about-mono{font-family:'JetBrains Mono',monospace;background:#0c0a08;border:1px solid #2a1f15;border-left:3px solid #C9A84C;padding:16px 20px;font-size:11px;color:#C9A84C;margin:18px 0;line-height:1.8;overflow-x:auto;}
.about-quote{font-style:italic;color:#8B7355;border-left:2px solid #2a1f15;padding-left:20px;margin:24px 0;font-size:13px;line-height:1.8;}
.verify-link{display:inline-block;margin-top:24px;padding:10px 24px;border:1px solid #C9A84C;color:#C9A84C;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;text-decoration:none;transition:all .2s;}
.verify-link:hover{background:#C9A84C;color:#0D0B0E;}
.stat-row{display:flex;flex-wrap:wrap;gap:16px;margin:20px 0;}
.stat-box{flex:1;min-width:140px;background:#0c0a08;border:1px solid #2a1f15;padding:16px;text-align:center;}
.stat-num{font-family:'JetBrains Mono',monospace;font-size:22px;color:#C9A84C;display:block;}
.stat-label{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#8B7355;margin-top:4px;display:block;}

.explorer-panel{display:none;max-width:1100px;margin:0 auto;padding:30px 20px 80px;}
.explorer-panel.visible{display:block;}
.exp-section{margin-bottom:44px;}
.exp-h1{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#C9A84C;margin-bottom:16px;border-bottom:1px solid #2a1f15;padding-bottom:10px;display:flex;justify-content:space-between;align-items:center;}
.exp-table{width:100%;border-collapse:collapse;font-size:11px;}
.exp-table th{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#8B7355;padding:8px 10px;border-bottom:1px solid #2a1f15;text-align:left;}
.exp-table td{font-family:'JetBrains Mono',monospace;font-size:10px;color:#F0E6D3;padding:8px 10px;border-bottom:1px solid #150f0a;word-break:break-all;}
.exp-table tr:hover td{background:#0f0c09;}
.exp-bal{color:#C9A84C;font-weight:bold;}
.exp-sold{color:#8B7355;}
.exp-unsold{color:#4CAF7D;}
.exp-founder{color:#C9A84C;}
.exp-hash{font-size:8px;color:#5a4a35;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.exp-search{background:#0c0a08;border:1px solid #2a1f15;color:#F0E6D3;font-family:'JetBrains Mono',monospace;font-size:11px;padding:8px 14px;width:100%;max-width:400px;margin-bottom:16px;outline:none;}
.exp-search:focus{border-color:#C9A84C;}
.exp-stat-row{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:28px;}
.exp-stat{flex:1;min-width:120px;background:#0c0a08;border:1px solid #2a1f15;padding:14px;text-align:center;}
.exp-stat-num{font-family:'JetBrains Mono',monospace;font-size:20px;color:#C9A84C;display:block;}
.exp-stat-label{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#8B7355;margin-top:4px;display:block;}
.exp-badge{display:inline-block;padding:2px 7px;border-radius:2px;font-size:8px;letter-spacing:1px;text-transform:uppercase;}
.badge-sold{background:rgba(139,115,85,.15);border:1px solid #8B7355;color:#8B7355;}
.badge-unsold{background:rgba(76,175,125,.1);border:1px solid #4CAF7D;color:#4CAF7D;}
.badge-founder{background:rgba(201,168,76,.1);border:1px solid #C9A84C;color:#C9A84C;}
.exp-tabs{display:flex;gap:8px;margin-bottom:20px;}
.exp-tab{padding:6px 16px;background:#0c0a08;border:1px solid #2a1f15;color:#8B7355;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:1px;cursor:pointer;}
.exp-tab.active{border-color:#C9A84C;color:#C9A84C;}
.exp-content{display:none;}
.exp-content.active{display:block;}

/* ── INVITATION OVERLAY ─────────────────────────────── */
#invite-overlay{
  position:fixed;inset:0;z-index:9999;
  background:radial-gradient(ellipse at center, #1a0e05 0%, #0a0602 100%);
  display:flex;align-items:center;justify-content:center;
  transition:opacity .8s ease;
}
#invite-overlay.fade-out{opacity:0;pointer-events:none;}
#invite-overlay.gone{display:none;}

.invite-envelope{
  position:relative;width:320px;cursor:pointer;
  animation:floatEnv 3s ease-in-out infinite;
}
@keyframes floatEnv{
  0%,100%{transform:translateY(0);}
  50%{transform:translateY(-10px);}
}
.invite-envelope-body{
  width:320px;height:200px;
  background:linear-gradient(135deg,#1a0e05 0%,#2a1a08 50%,#1a0e05 100%);
  border:1px solid #8B5E2A;
  border-radius:4px;
  position:relative;
  box-shadow:0 20px 60px rgba(0,0,0,.8), inset 0 1px 0 rgba(201,168,76,.2);
}
.invite-envelope-flap{
  position:absolute;top:0;left:0;width:100%;
  border-left:160px solid transparent;
  border-right:160px solid transparent;
  border-top:100px solid #1a1005;
  filter:drop-shadow(0 2px 4px rgba(0,0,0,.5));
  transform-origin:top center;
  transition:transform .6s ease;
}
.invite-envelope.open .invite-envelope-flap{
  transform:rotateX(180deg);
}
.invite-wax{
  position:absolute;top:50%;left:50%;
  transform:translate(-50%,-50%);
  width:64px;height:64px;
  background:radial-gradient(circle,#8B0000 0%,#5a0000 60%,#3a0000 100%);
  border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 16px rgba(139,0,0,.6);
  font-size:24px;color:#C9A84C;
  font-family:'JetBrains Mono',monospace;
  transition:transform .3s, box-shadow .3s;
}
.invite-envelope:hover .invite-wax{
  transform:translate(-50%,-50%) scale(1.1);
  box-shadow:0 6px 24px rgba(139,0,0,.8);
}
.invite-hint{
  text-align:center;margin-top:20px;
  font-family:'Cormorant Garamond',serif;
  font-style:italic;font-size:16px;
  color:#8B7355;letter-spacing:1px;
  animation:pulse 2s ease-in-out infinite;
}
@keyframes pulse{0%,100%{opacity:.6;}50%{opacity:1;}}

/* ── LETTER PANEL ───────────────────────────────────── */
#invite-letter{
  display:none;
  max-width:400px;width:90%;
  background:linear-gradient(160deg,#1a1208 0%,#0f0c06 100%);
  border:1px solid #8B5E2A;
  padding:36px 32px;
  position:relative;
  box-shadow:0 30px 80px rgba(0,0,0,.9);
  animation:letterRise .5s ease;
}
@keyframes letterRise{from{opacity:0;transform:translateY(30px);}to{opacity:1;transform:translateY(0);}}
.letter-omega{
  text-align:center;font-size:48px;color:#C9A84C;
  font-family:'JetBrains Mono',monospace;
  margin-bottom:16px;
  text-shadow:0 0 30px rgba(201,168,76,.4);
}
.letter-title{
  font-family:'Cormorant Garamond',serif;
  font-size:22px;font-style:italic;
  color:#F0E6D3;text-align:center;
  margin-bottom:8px;letter-spacing:1px;
}
.letter-subtitle{
  font-family:'Cormorant Garamond',serif;
  font-size:13px;color:#8B7355;
  text-align:center;margin-bottom:28px;
  font-style:italic;
}
.letter-divider{
  border:none;border-top:1px solid #2a1f15;margin:20px 0;
}
.letter-body{
  font-family:'Cormorant Garamond',serif;
  font-size:15px;color:#d4c9b8;
  line-height:1.8;text-align:center;
  margin-bottom:28px;font-style:italic;
}
.invite-paths{
  display:flex;flex-direction:column;gap:10px;
}
.invite-path{
  padding:12px 20px;
  background:rgba(201,168,76,.05);
  border:1px solid #2a1f15;
  color:#C9A84C;
  font-family:'JetBrains Mono',monospace;
  font-size:10px;letter-spacing:2px;
  text-transform:uppercase;
  cursor:pointer;
  transition:all .2s;
  text-align:center;
}
.invite-path:hover{
  background:rgba(201,168,76,.12);
  border-color:#C9A84C;
  transform:translateX(4px);
}
.letter-sig{
  font-family:'Cormorant Garamond',serif;
  font-size:13px;color:#8B7355;
  text-align:center;margin-top:24px;
  font-style:italic;
}

</style>
</style>
</head>
<body>

<!-- ── INVITATION OVERLAY ──────────────────────────── -->
<div id="invite-overlay">
  <div style="display:flex;flex-direction:column;align-items:center;">

    <!-- Envelope (shown first) -->
    <div id="invite-envelope-wrap">
      <div class="invite-envelope" id="invite-env" onclick="openEnvelope()">
        <div class="invite-envelope-body">
          <div class="invite-envelope-flap" id="env-flap"></div>
          <div class="invite-wax">Ω</div>
        </div>
      </div>
      <div class="invite-hint">Tap to open your invitation</div>
    </div>

    <!-- Letter (shown after tap) -->
    <div id="invite-letter">
      <div class="letter-omega">Ω</div>
      <div class="letter-title">You Are Cordially Invited</div>
      <div class="letter-subtitle">to the Omega Art Studio</div>
      <hr class="letter-divider">
      <div class="letter-body">
        Where cryptography meets surrealism.<br>
        Where every token is a permanent truth<br>
        inscribed on an immutable ledger.<br><br>
        Choose your path.
      </div>
      <div class="invite-paths">
        <div class="invite-path" onclick="enterPath('gallery')">
          ✦ &nbsp; Omega Art Studio &nbsp; ✦
        </div>
        <div class="invite-path" onclick="enterPath('explorer')">
          ✦ &nbsp; Omega Ledger &nbsp; ✦
        </div>
        <div class="invite-path" onclick="enterPath('about')">
          ✦ &nbsp; About Omega &nbsp; ✦
        </div>
      </div>
      <div class="letter-sig">
        — Thomas Lee Harvey, Founder
      </div>
    </div>

  </div>
</div>

<script>
function openEnvelope() {
  document.getElementById('env-flap').style.transform = 'rotateX(180deg)';
  setTimeout(function() {
    document.getElementById('invite-envelope-wrap').style.display = 'none';
    document.getElementById('invite-letter').style.display = 'block';
  }, 600);
}

function enterPath(tab) {
  var overlay = document.getElementById('invite-overlay');
  overlay.classList.add('fade-out');
  setTimeout(function() {
    overlay.classList.add('gone');
    showTab(tab);
  }, 800);
}
</script>

<header>
  <h1>OMEGA ART STUDIO</h1>
  <div class="status" id="status">Loading...</div>
  <pre id="debug"></pre>
</header>
<div class="tab-nav">
  <button class="tab-btn active" onclick="showTab('gallery')">Gallery</button>
  <button class="tab-btn" onclick="showTab('about')">About Omega</button>
  <button class="tab-btn" onclick="showTab('explorer')">Ω Ledger</button>
</div>
<div id="gallery-panel">
<div class="filters" id="filters"></div>
<div id="gallery"></div></div>
<div id="about-panel">

  <div class="about-section">
    <div class="about-h1">The Story</div>
    <div class="about-p">
      There is a game being played. You may not have noticed it yet. Thomas Lee Harvey has been leaving messages inside the art — not signatures, not watermarks, but intentions. Symbols that recur across collections. Figures that face the wrong direction. Costumes that should not exist. Each collection is a move in a game that has no published rules, only clues. Surrealism was always a game. Dalí knew it. Magritte knew it. The pipe was never a pipe. The melting clock was never about time.
    </div>
    <div class="about-p">
      Omega was built by one person. No laptop. No team. No external funding. No cloud provider. Two Android phones, a terminal emulator, and an architecture that most funded engineering teams have never attempted. What exists today is a complete distributed financial operating system, a cryptographic art authentication layer, a live NFT marketplace, and a virtual card issuance system — all running on hardware that fits in two pockets.
    </div>
    <div class="about-p">
      That is not a metaphor or a marketing line. The database is PostgreSQL 18.2 running on a physical Android phone, accessed over SSH from a second phone acting as the control plane. The consensus engine enforces Byzantine fault-tolerant approval across two physical nodes. The ledger has recorded over <strong>2,020,075 immutable entries</strong>. Its own trigger has blocked its creator from deleting a single row. The system protects itself from everyone — including Thomas.
    </div>
    <div class="about-p">
      This was built in sessions. Late nights. One patch at a time. Every component self-grades through a 17-part Oracle that cannot regress. Every number in this system is real — pulled from the database, not written into a document.
    </div>
    <div class="about-quote">"I didn't build a portfolio project. I built infrastructure. The ledger doesn't care who created it — it blocks everyone equally."<br>— Thomas Lee Harvey</div>
    <div class="stat-row">
      <div class="stat-box"><span class="stat-num">2M+</span><span class="stat-label">Ledger Entries</span></div>
      <div class="stat-box"><span class="stat-num">500</span><span class="stat-label">Authenticated NFTs</span></div>
      <div class="stat-box"><span class="stat-num">125</span><span class="stat-label">Database Tables</span></div>
      <div class="stat-box"><span class="stat-num">2</span><span class="stat-label">Android Phones</span></div>
    </div>
  </div>

  <div class="about-section">
    <div class="about-h1">Omega Bank — The Ledger That Knows What a Dollar Is</div>
    <div class="about-p">
      Bitcoin does not know what a dollar is. Ethereum does not know what a dollar is. They are protocols for moving tokens between addresses. When you buy something on-chain, the blockchain records a hash. It does not record a sale. It does not record a counterparty. It does not record a currency. It records a state transition and calls it ownership. That is not ownership. That is a pointer.
    </div>
    <div class="about-p">
      <strong>Omega Ledger knows what a dollar is.</strong> Every transaction is denominated in USD. Every entry is double-entry bookkeeping — a debit and a credit, balanced to the cent, SHA-256 hash-chained, ISO 20022 compliant. Every NFT purchase writes a real financial record: who paid, how much, which asset transferred, and when. Not a token transfer. A transaction. The same standard that moves money between banks. Applied to art. On two phones.
    </div>
    <div class="about-p">
      When you buy an Omega NFT, three things happen simultaneously: a Stripe payment clears in USD, an immutable ledger entry is written with your identity as the new owner, and an OM109 cryptographic fingerprint ties the art to the financial record permanently. The art and the money are the same ledger entry. No other NFT platform does this because no other NFT platform has a real financial ledger underneath it.
    </div>
    <div class="about-p">
      The ledger uses 7-layer double-entry accounting with SHA-256 hash chaining. Every entry references the hash of the entry before it. Tampering with any record breaks every record after it. The chain is the proof. There is no admin override. There is no rollback. The immutability trigger has blocked its own creator.
    </div>
    <div class="about-mono">
omega_bank     → 125 tables · PostgreSQL 18.2 · Phone 2 (ARM64)
omega_ledger   → 39 tables  · NFT registry · provenance · COAs
entries        → 2,020,075+ · immutable · SHA-256 hash-chained
consensus      → Byzantine fault-tolerant · 2-node quorum
ISO 20022      → pain.001 XML · auto-generated on every INSERT
    </div>
  </div>

  <div class="about-section">
    <div class="about-h1">OM109 — A Cryptographic Primitive Built From Scratch</div>
    <div class="about-p">
      OM109 is Thomas Lee Harvey's original dual-key alternating signature algorithm — named after his birthday, October 9th. It was invented specifically for Omega. Not adopted. Not wrapped. Invented. It signs every financial transaction and every piece of art using the same primitive, creating a single cryptographic thread that runs through the entire system.
    </div>
    <div class="about-mono">
genesis     = SHA256(GENESIS_SEED)
sig_a       = SHA256(genesis + ":A:" + token_id + ":" + image_hash)
sig_b       = SHA256(genesis + ":B:" + token_id + ":" + image_hash + ":" + sig_a)
fingerprint = SHA256(sig_a[:32] + sig_b[:32])
    </div>
    <div class="about-p">
      Zero collisions across all 400 tokens across all four collections. When you buy an Omega NFT, the OM109 fingerprint of your token is written into the financial ledger at the moment of purchase. The art provenance and the payment record share the same cryptographic root. <strong>The art and the money are the same ledger entry.</strong>
    </div>
    <div class="about-quote">"The same primitive that secures a dollar transfer secures a piece of art. That is not a coincidence. That is architecture."</div>
  </div>

  <div class="about-section">
    <div class="about-h1">The Art — Hyper-Surrealism</div>
    <div class="about-p">
      The four collections — <strong>Echoes of Eternity, Somnium, Paracosm, Monolith</strong> — are not generative noise. They are a defined aesthetic movement: Hyper-Surrealism. Where classical Surrealism reached for the unconscious through paint and canvas — where Dalí dripped clocks and Magritte hid faces behind fruit — Hyper-Surrealism reaches for it through neural computation. Latent space as dreamscape. Diffusion as vision. The model's hallucination as the artist's intention made visible.
    </div>
    <div class="about-p">
      Thomas does not describe what he wants the model to produce. He describes what cannot exist — and then makes it exist. Clouds that are also faces. Gold that is also grief. A figure that is simultaneously costume and identity, mask and self. Every piece is a subliminal transmission. The symbols recur. The geometry repeats. If you have looked at more than one collection, you have already received messages you have not yet decoded.
    </div>
    <div class="about-p">
      This is a surrealist game of Clue — but the weapon is a fingerprint, the room is a ledger, and the suspect is whoever holds the token. Every collection is a chapter. Every rarity tier is a clue. The Impossible Diamond is not a reward for spending more. It is an invitation to look closer.
    </div>
    <div class="about-p">
      Every image was generated on ARM64 hardware using Stable Diffusion, with rarity seeded deterministically. The rarity is not assigned after the fact. It is computed from the token ID at mint time and cannot be changed. An Impossible Diamond was always going to be an Impossible Diamond.
    </div>
    <div class="about-p">
      Thomas personally holds one Impossible Diamond in every collection. Not as a collector. As a founder. The first four entries in the registry — one per collection — permanently founder-linked, permanently immutable.
    </div>
    <div class="about-mono">
Echoes of Eternity  · #0085 "Stasis"    · Thomas Diamond
Somnium             · #0017 "Aloft"     · Thomas Diamond
Paracosm            · #1002 "Obelisk"   · Thomas Diamond
Monolith            · #2005 "Founder"   · Thomas Diamond
    </div>
  </div>

  <div class="about-section">
    <div class="about-h1">Bal de Rêves — The Next Collection</div>
    <div class="about-p">
      In 1972, the Rothschild family hosted a masquerade ball at Château de Ferrières. Dalí attended. The costumes were impossible — antlered headdresses cast in gold, birdcages worn as crowns, a man with an apple for a face. It was not a party. It was a séance. It was Surrealism in formal wear, sitting down to dinner and refusing to leave.
    </div>
    <div class="about-p">
      The next Omega collection is <strong>Bal de Rêves — The Ball of Dreams</strong>. Each NFT is a character. Each character wears a costume that should not exist. The collection is structured like a deck of graded trading cards — because every piece deserves to be handled like one.
    </div>
    <div class="about-p">
      Rarity is visible at the edge. <strong>Impossible Diamond</strong> cards carry a double hairline rule in diamond-grade finish — ultra rare, unmistakable. <strong>Ultra Rare</strong> cards have a gold border. <strong>Rare</strong> cards carry silver. <strong>Bronze</strong> gets a warm metallic edge. <strong>Common</strong> cards have no border — but every card in the deck is graded, weighted, and feels like it was pulled from a vault.
    </div>
    <div class="about-p">
      The ball is still going. The invitation arrives when the collection drops.
    </div>
    <div class="about-quote">"Every guest at the ball wore a face that wasn't theirs. Every token in the ledger carries a fingerprint that cannot be faked. The costume is the art. The fingerprint is the proof."<br>— Thomas Lee Harvey</div>
  </div>

  <div class="about-section">
    <div class="about-h1">What You Own When You Buy</div>
    <div class="about-p">
      When your Stripe payment clears, Omega delivers a museum-grade provenance package. Four documents. One chain of custody. Permanent record.
    </div>
    <div class="about-p">
      <strong>Certificate of Authenticity (COA)</strong> — a cryptographically signed document bearing the token ID, collection, rarity, SHA-256 image hash, and OM109 fingerprint. This is the primary ownership document. It is generated at the moment of purchase and tied to your identity in the ledger.
    </div>
    <div class="about-p">
      <strong>Art Passport</strong> — the travel document for the piece. Every collection the token has passed through, every wallet that has held it, every transfer recorded in the immutable ledger. A physical museum issues a provenance record that may span decades. Omega issues one at the moment of mint and updates it with every transfer. Permanently.
    </div>
    <div class="about-p">
      <strong>OM109 Fingerprint Certificate</strong> — the cryptographic root document. The dual-key signature computed at mint, the genesis seed, the image hash inputs, and the final fingerprint output. This is the document that allows independent verification of authenticity without trusting Omega at all. The math speaks for itself.
    </div>
    <div class="about-p">
      <strong>Provenance Scroll</strong> — the complete chain of custody from genesis to your wallet. Every ledger entry, every hash, every timestamp. Formatted for archival. Designed to outlast the platform that issued it.
    </div>
    <div class="about-p">
      You also own the PNG — the actual artwork, full resolution, generated on ARM64 hardware, yours to preserve. <strong>This is a digital asset. The PNG, the certificates, the fingerprint — these are your responsibility to keep.</strong> Omega provides the provenance. The ledger provides the permanent record. You hold the asset.
    </div>
    <a class="verify-link" href="https://omegaledgernode.netlify.app/health" target="_blank">Verify on Omega Ledger →</a>
  </div>

  <div class="about-section">
    <div class="about-h1">Thomas Lee Harvey</div>
    <div class="about-p">
      Self-taught. No team. No funding. No laptop. No cloud provider. Thomas Lee Harvey built a Byzantine consensus financial system, an immutable hash-chained ledger with over two million entries, a dual-key cryptographic signature algorithm he invented and named after his birthday, virtual card issuance with Luhn-valid PANs and AES-256 encryption, four generative art collections with deterministic rarity, and a live NFT marketplace with Stripe checkout and museum-grade provenance delivery — entirely on two Android phones in a terminal emulator, on ARM64 hardware, with no external dependencies beyond a free Cloudflare tunnel.
    </div>
    <div class="about-p">
      He has been leaving messages in the art since the first collection. Whether you find them depends on how closely you look. The game is already in progress. The ledger has already recorded your move.
    </div>
    <div class="about-p">
      The discipline that makes it trustworthy is the same discipline that built it. Every number is verified against the database before it is stated. Every patch compiles before it runs. Every component self-grades every session. The Oracle has never been manually reset. The immutability trigger has never been bypassed. The ledger has never been edited. When the system found a bug, it was fixed and documented — not hidden. That is what integrity looks like in infrastructure.
    </div>
    <div class="about-quote">"Omega Ledger knows what a dollar is. Bitcoin doesn't. Ethereum doesn't. I built a financial system that authenticates art, issues cards, verifies provenance, and denominates everything in dollars — from first principles, on hardware that fits in a pocket. No team. No funding. No excuses."<br>— Thomas Lee Harvey, CEO &amp; Founder</div>
  </div>

</div>


<div id="explorer-panel" class="explorer-panel" style="padding:0;overflow:hidden;">
  <iframe src="omega_explorer.html" style="width:100%;height:82vh;border:none;display:block;"></iframe>
</div>

<script>
var expTokensAll = [];

function expTab(name) {
  document.querySelectorAll('.exp-content').forEach(function(el){ el.classList.remove('active'); });
  document.querySelectorAll('.exp-tab').forEach(function(el){ el.classList.remove('active'); });
  document.getElementById('exp-' + name).classList.add('active');
  event.target.classList.add('active');
  if (name === 'tokens' && expTokensAll.length === 0) loadTokens();
  if (name === 'ledger') loadLedger();
}

function loadExplorer() {
  // Stats
  fetch(API_URL + '/ledger/stats')
    .then(function(r){ return r.json(); })
    .then(function(d){
      var stats = [
        {num: d.total_tokens || 400, label: 'Total NFTs'},
        {num: d.sold || 0, label: 'Sold'},
        {num: d.unsold || 0, label: 'Available'},
        {num: '$' + (997600000).toLocaleString(), label: 'Ledger Value'},
      ];
      document.getElementById('exp-stats').innerHTML = stats.map(function(s){
        return '<div class="exp-stat"><span class="exp-stat-num">' + s.num + '</span><span class="exp-stat-label">' + s.label + '</span></div>';
      }).join('');
    }).catch(function(){});

  // Wallets
  fetch(API_URL + '/founding-wallets')
    .then(function(r){ return r.json(); })
    .then(function(d){
      var wallets = d.founding_wallets || [];
      var html = wallets.map(function(w){
        var bal = parseFloat(w.balance);
        var balStr = isNaN(bal) ? w.balance : '$' + bal.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
        var shortId = w.wallet_id ? w.wallet_id.substring(0,8) + '...' : 'N/A';
        return '<tr>' +
          '<td>' + (w.name || 'Unknown') + '</td>' +
          '<td><span class="exp-hash" title="' + (w.wallet_id||'') + '">' + (w.wallet_id||'N/A') + '</span></td>' +
          '<td class="exp-bal">' + balStr + '</td>' +
          '<td>' + (w.nft_count || 0) + ' tokens</td>' +
          '</tr>';
      }).join('');
      document.getElementById('wallets-body').innerHTML = html || '<tr><td colspan="4" style="color:#8B7355;text-align:center;">No data</td></tr>';
    }).catch(function(e){ document.getElementById('wallets-body').innerHTML = '<tr><td colspan="4" style="color:#8B7355;text-align:center;">Error loading wallets</td></tr>'; });
}

function loadTokens() {
  var colls = ['echoes','somnium','paracosm','monolith','le-bal','realism-punks'];
  var all = [];
  var done = 0;
  colls.forEach(function(c){
    fetch(API_URL + '/collection/' + c)
      .then(function(r){ return r.json(); })
      .then(function(d){
        (d.tokens || []).forEach(function(t){ t._coll = c; all.push(t); });
        done++;
        if (done === colls.length) {
          expTokensAll = all.sort(function(a,b){ return a.token_id - b.token_id; });
          renderTokens(expTokensAll);
        }
      }).catch(function(){ done++; });
  });
}

function renderTokens(tokens) {
  var html = tokens.map(function(t){
    var status = t.sale_status || 'unsold';
    var badgeClass = status === 'sold' ? 'badge-sold' : status === 'founder' ? 'badge-founder' : 'badge-unsold';
    var minted = t.minted_at ? t.minted_at.substring(0,10) : 'N/A';
    var fp = t.om109_fingerprint ? t.om109_fingerprint.substring(0,16) + '...' : 'N/A';
    return '<tr>' +
      '<td>' + t.token_id + '</td>' +
      '<td>' + (t.collection || t._coll || '') + '</td>' +
      '<td>' + (t.title || '') + '</td>' +
      '<td>' + (t.rarity || '') + '</td>' +
      '<td><span class="exp-badge ' + badgeClass + '">' + status + '</span></td>' +
      '<td><span class="exp-hash" title="' + (t.om109_fingerprint||'') + '">' + fp + '</span></td>' +
      '<td>' + minted + '</td>' +
      '</tr>';
  }).join('');
  document.getElementById('tokens-body').innerHTML = html || '<tr><td colspan="7" style="color:#8B7355;text-align:center;">No tokens</td></tr>';
}

function filterTokens() {
  var q = document.getElementById('token-search').value.toLowerCase();
  if (!q) { renderTokens(expTokensAll); return; }
  renderTokens(expTokensAll.filter(function(t){
    return (t.token_id+'').includes(q) ||
           (t.title||'').toLowerCase().includes(q) ||
           (t.collection||'').toLowerCase().includes(q) ||
           (t.rarity||'').toLowerCase().includes(q);
  }));
}

function loadLedger() {
  fetch(API_URL + '/ledger/stats')
    .then(function(r){ return r.json(); })
    .then(function(d){
      var entries = d.recent_entries || d.entries || [];
      if (!entries.length) {
        document.getElementById('ledger-body').innerHTML = '<tr><td colspan="8" style="color:#8B7355;text-align:center;padding:30px;">No recent entries — add /ledger/recent endpoint to provenance API for full history</td></tr>';
        return;
      }
      var html = entries.map(function(e){
        return '<tr>' +
          '<td>' + (e.created_at||'').substring(0,19) + '</td>' +
          '<td>' + (e.event_type||'') + '</td>' +
          '<td>' + (e.collection||'') + '</td>' +
          '<td>' + (e.token_id||'') + '</td>' +
          '<td class="exp-hash">' + (e.from_account||'').substring(0,12) + '</td>' +
          '<td class="exp-hash">' + (e.to_account||'').substring(0,12) + '</td>' +
          '<td>' + (e.amount_usd ? '$'+parseFloat(e.amount_usd).toFixed(2) : '') + '</td>' +
          '<td class="exp-hash">' + (e.chain_hash||'').substring(0,16) + '</td>' +
          '</tr>';
      }).join('');
      document.getElementById('ledger-body').innerHTML = html;
    }).catch(function(){
      document.getElementById('ledger-body').innerHTML = '<tr><td colspan="8" style="color:#8B7355;text-align:center;">Add /ledger/recent to provenance API</td></tr>';
    });
}
</script>

<script>
function getResolution(collection) {
  var res = {
    'Echoes of Eternity': '665 x 886 px',
    'Somnium': '768 x 1024 px',
    'Paracosm': '677 x 870 px',
    'Monolith': '768 x 768 px'
  };
  return res[collection] || 'High Resolution';
}

function showTab(tab) {
  var gp = document.getElementById('gallery-panel');
  var ap = document.getElementById('about-panel');
  var ep = document.getElementById('explorer-panel');
  var btns = document.querySelectorAll('.tab-nav .tab-btn');
  gp.classList.add('hidden');
  ap.classList.remove('visible');
  ep.classList.remove('visible');
  btns[0].classList.remove('active');
  btns[1].classList.remove('active');
  if (btns[2]) btns[2].classList.remove('active');
  if (tab === 'gallery') {
    gp.classList.remove('hidden');
    btns[0].classList.add('active');
  } else if (tab === 'about') {
    ap.classList.add('visible');
    btns[1].classList.add('active');
  } else if (tab === 'explorer') {
    ep.classList.add('visible');
    if (btns[2]) btns[2].classList.add('active');
    loadExplorer();
  }
}
</script>


<script>
var API_URL = 'https://wet-faced-thou-webster.trycloudflare.com';
// Dynamic API URL — fetch from broker on load
(async function() {
  try {
    var r = await fetch('http://127.0.0.1:8085/current-api');
    var d = await r.json();
    if (d.api) API_URL = d.api;
  } catch(e) {}
})();
var COLLECTIONS = ['echoes', 'somnium', 'paracosm', 'monolith', 'le-bal', 'realism-punks'];
var FOLDER_MAP = {
  'Echoes of Eternity': { folder: 'echoes_of_eternity', pad: 4 },
  'Somnium':            { folder: 'somnium',            pad: 4 },
  'Paracosm':           { folder: 'paracosm',            pad: 4 },
  'Monolith':           { folder: 'monolith',            pad: 4 },
  'Le Bal des Rêves':   { folder: 'le_bal_des_reves',   pad: 4 },
  'Realism Punks':      { folder: 'realism_punks',       pad: 4 }
};
var ALL_TOKENS = [];
var currentFilter = 'all';

function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}
function debugLog(msg) {
  var d = document.getElementById('debug');
  d.textContent += msg + '\\n';
}
function getImagePath(token) {
  var info = FOLDER_MAP[token.collection];
  if (!info) return '';
  var idStr = String(token.token_id).padStart(info.pad, '0');
  return '/' + info.folder + '/images/' + idStr + '.png';
}

async function loadAll() {
  setStatus('Loading from ' + API_URL + '...');
  var tokens = [];
  for (var i = 0; i < COLLECTIONS.length; i++) {
    var slug = COLLECTIONS[i];
    try {
      var r = await fetch(API_URL + '/collection/' + slug);
      if (!r.ok) { debugLog('HTTP ' + r.status + ' for ' + slug); continue; }
      var data = await r.json();
      if (!data.tokens || !data.tokens.length) { debugLog('No tokens for ' + slug); continue; }
      tokens = tokens.concat(data.tokens);
    } catch(e) {
      debugLog('Fetch error (' + slug + '): ' + e.message);
    }
  }
  if (tokens.length === 0) {
    setStatus('FAILED — no tokens loaded. Check debug log above.');
    return;
  }
  ALL_TOKENS = tokens.sort(function(a,b){ return a.token_id - b.token_id; });
  setStatus(ALL_TOKENS.length + ' tokens loaded');
  buildFilters();
  render();
}

function buildFilters() {
  var colls = ['all', 'Echoes of Eternity', 'Somnium', 'Paracosm', 'Monolith', 'Le Bal des Rêves'];
  var wrap = document.getElementById('filters');
  wrap.innerHTML = colls.map(function(c) {
    var label = c === 'all' ? 'All (' + ALL_TOKENS.length + ')' : c;
    return '<button class="filter-btn' + (c === 'all' ? ' active' : '') + '" data-c="' + c + '">' + label + '</button>';
  }).join('');
  wrap.querySelectorAll('.filter-btn').forEach(function(btn) {
    btn.onclick = function() {
      currentFilter = btn.dataset.c;
      wrap.querySelectorAll('.filter-btn').forEach(function(b){ b.classList.remove('active'); });
      btn.classList.add('active');
      render();
    };
  });
}

function openFullscreen(src, title) {
  var modal = document.getElementById('fullscreen-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'fullscreen-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;';
    modal.onclick = function(){ modal.style.display='none'; };
    document.body.appendChild(modal);
  }
  modal.innerHTML = '<img src="' + src + '" style="max-width:95vw;max-height:90vh;object-fit:contain;">' +
    '<div style="color:#C9A84C;font-family:\\'Cormorant Garamond\\',serif;font-size:14px;margin-top:12px;letter-spacing:1px;">' + title + '</div>' +
    '<div style="color:#8B7355;font-size:10px;margin-top:6px;">Tap anywhere to close</div>';
  modal.style.display = 'flex';
}

function render() {
  var filtered = currentFilter === 'all' ? ALL_TOKENS : ALL_TOKENS.filter(function(t){ return t.collection === currentFilter; });
  var gallery = document.getElementById('gallery');
  gallery.innerHTML = filtered.map(function(t) {
    var img = getImagePath(t);
    return '<div class="card-wrap" onclick="this.classList.toggle(\\'flipped\\')" ondblclick="event.stopPropagation(); openFullscreen(\\'' + img + '\\', \\'' + t.title.replace(/'/g,"\\\\'") + '\\')">' +
      '<div class="card">' +
        '<div class="face face-front">' +
          '<img src="' + img + '" alt="' + t.title + '" loading="lazy" onerror="this.parentElement.style.background=\\'#0D0B0E\\'; this.style.display=\\'none\\';">' +
          '<div class="rarity-tag">' + (t.rarity||'?') + '</div>' +
          (t.sale_status==='sold'?'<div class="sold-overlay"><div class="sold-badge">Sold</div></div>':'') +
          '<div class="card-caption">#' + t.token_id + ' — ' + t.title + '</div>' +
        '</div>' +
        '<div class="face face-back">' +
          '<div style="text-align:center;border-bottom:1px solid #C9A84C;margin-bottom:8px;padding-bottom:6px;">' +
            '<div style="font-family:\\'Cormorant Garamond\\',serif;font-size:11px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Certificate of Authenticity</div>' +
            '<div style="font-size:8px;color:#8B7355;margin-top:2px;font-style:italic;">Omega Art Studio · Thomas Lee Harvey</div>' +
          '</div>' +
          '<div class="back-row"><div class="back-label">Title</div><div class="back-value">' + t.title + '</div></div>' +
          '<div class="back-row"><div class="back-label">Collection</div><div class="back-value">' + t.collection + '</div></div>' +
          '<div class="back-row"><div class="back-label">Resolution</div><div class="back-value">' + getResolution(t.collection) + '</div></div>' +
          '<div class="back-row"><div class="back-label">Rarity</div><div class="back-value">' + t.rarity + '</div></div>' +
          '<div class="back-row"><div class="back-label">SHA-256</div><div class="back-value">' + (t.image_sha256||'').substring(0,32) + '...</div></div>' +
          '<div class="back-row"><div class="back-label">OM109</div><div class="back-value">' + (t.om109_fingerprint||'').substring(0,32) + '...</div></div>' +
          '<div class="back-row"><div class="back-label">Chain Hash</div><div class="back-value">' + (t.chain_hash||'').substring(0,32) + '...</div></div>' +
          '<div style="margin-top:10px;border-top:1px solid #3a2e1e;padding-top:10px;">' +
            (t.sale_status === 'sold' ?
              '<div style="text-align:center;background:#1C1612;border:1px solid #8B7355;color:#8B7355;padding:8px;font-size:10px;letter-spacing:2px;font-family:\\'JetBrains Mono\\',monospace;">SOLD</div>'
              : t.is_founder_linked ?
              '<div style="text-align:center;color:#8B7355;font-size:9px;font-style:italic;">Founder Held · Not For Sale</div>'
              : t.stripe_payment_link ?
              '<button onclick="event.stopPropagation();addToCart(' + t.token_id + ',\\''+t.collection+'\\',\\''+t.title+'\\',\\''+t.rarity+'\\',\\''+t.stripe_payment_link+'\\')" style="display:block;width:100%;background:#C9A84C;color:#0D0B0E;padding:8px;font-size:10px;letter-spacing:2px;font-weight:bold;text-transform:uppercase;border:none;cursor:pointer;font-family:\\'JetBrains Mono\\',monospace;">Add to Cart · ' + ({"Impossible Diamond":"$2,500","Black Diamond":"$500","Super Rare":"$150","Rare":"$75","Medium":"$35","Common":"$15"}[t.rarity]||"$15") + '</button>'
              : '<div style="text-align:center;color:#8B7355;font-size:9px;">Not available</div>'
            ) +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');
}

loadAll();

const PRICES={"Impossible Diamond":2500,"Black Diamond":500,"Super Rare":150,"Rare":75,"Medium":35,"Common":15};
let cart=JSON.parse(localStorage.getItem('omega_cart')||'[]');

function saveCart(){localStorage.setItem('omega_cart',JSON.stringify(cart));renderCart();}

function addToCart(tokenId,collection,title,rarity,stripeLink){
  const key=collection+'_'+tokenId;
  if(cart.find(i=>i.key===key)){toggleCart();return;}
  cart.push({key,tokenId,collection,title,rarity,stripeLink});
  saveCart();
  toggleCart();
}

function removeFromCart(key){cart=cart.filter(i=>i.key!==key);saveCart();}

function toggleCart(){
  document.getElementById('cart-drawer').classList.toggle('open');
  document.getElementById('cart-overlay').classList.toggle('open');
}

function renderCart(){
  const badge=document.getElementById('cart-badge');
  const items=document.getElementById('cart-items');
  const footer=document.getElementById('cart-footer');
  const total=document.getElementById('cart-total');
  badge.style.display=cart.length?'flex':'none';
  badge.textContent=cart.length;
  if(!cart.length){items.innerHTML='<div class="cart-empty">Your collection is empty</div>';footer.style.display='none';return;}
  let sum=0;
  items.innerHTML=cart.map(item=>{
    const p=PRICES[item.rarity]||15;sum+=p;
    return '<div class="cart-item"><div class="cart-item-info"><div class="cart-item-title">'+item.title+'</div><div class="cart-item-sub">'+item.collection+' #'+String(item.tokenId).padStart(4,'0')+' · '+item.rarity+'</div></div><div class="cart-item-price">$'+p.toLocaleString()+'</div><button class="cart-remove" onclick="removeFromCart(\\''+item.key+'\\')">✕</button></div>';
  }).join('');
  total.textContent='$'+sum.toLocaleString();
  footer.style.display='block';
}

function checkout(){
  if(!cart.length)return;
  cart.forEach((item,i)=>setTimeout(()=>window.open(item.stripeLink,'_blank'),i*500));
}

renderCart();

</script>

<div id="cart-icon" onclick="toggleCart()">🛒<span id="cart-badge" style="display:none;">0</span></div>
<div id="cart-overlay" onclick="toggleCart()"></div>
<div id="cart-drawer">
  <div class="cart-header">
    <div class="cart-title">Your Collection</div>
    <button class="cart-close" onclick="toggleCart()">✕</button>
  </div>
  <div id="cart-items"><div class="cart-empty">Your collection is empty</div></div>
  <div id="cart-footer" style="display:none;">
    <div class="cart-total-row">
      <div class="cart-total-label">Total</div>
      <div class="cart-total-amt" id="cart-total">$0</div>
    </div>
    <button class="checkout-btn" onclick="checkout()">Checkout →</button>
  </div>
</div>
</body>
</html>
`;

function GalleryView({ onGoHome }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "#07100d", zIndex: 50, display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: "#0D0B0E", borderBottom: "1px solid #2a1f15" }}>
        <button onClick={onGoHome} style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 12px", borderRadius: 8, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: "#C9A84C", fontSize: "0.72rem", cursor: "pointer" }}>
          <HomeIcon className="w-3.5 h-3.5" /> Home
        </button>
        <span style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", fontFamily: "'JetBrains Mono', monospace" }}>Omega Gallery — embedded, unmodified</span>
      </div>
      <iframe
        title="Omega Gallery"
        srcDoc={OMEGA_GALLERY_HTML}
        sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
        style={{ flex: 1, width: "100%", border: "none" }}
      />
    </div>
  );
}

const DEFAULT_APPS = [
  { id: "chat", name: "Omega Chat", desc: "Deep AI conversation", icon: "Ω", kind: "internal", status: "live" },
  { id: "agent", name: "Omega Agent", desc: "Sandbox + live console", icon: "⌁", kind: "internal", status: "live" },
  { id: "gallery", name: "Omega Gallery", desc: "NFT platform · Stripe checkout — live, embedded", icon: "🖼️", kind: "internal", status: "live" },
  { id: "ledger", name: "Omega Ledger", desc: "Double-entry financial core", icon: "📒", kind: "link", status: "connect", url: "" },
  { id: "explorer", name: "Ledger Explorer", desc: "XRP-style block explorer", icon: "🔎", kind: "link", status: "connect", url: "" },
  { id: "wallet", name: "Omega Wallet", desc: "Self-custody holdings — address, transfer, list/sell", icon: "👛", kind: "planned", status: "planned" },
  { id: "om109", name: "OM109 Signature", desc: "Authenticate art, property deeds, documents", icon: "✒️", kind: "planned", status: "planned" },
  { id: "oracle", name: "Oracle Grading", desc: "System integrity scoring, as a licensable product", icon: "🏅", kind: "planned", status: "planned" },
  { id: "qin", name: "Qin Trading Bot", desc: "Automated trading engine", icon: "📈", kind: "planned", status: "planned" },
  { id: "powerball", name: "Quantum Powerball", desc: "20yr historical lottery model", icon: "🎱", kind: "planned", status: "planned" },
  { id: "b2b", name: "Omega B2B", desc: "Enterprise portal", icon: "🏢", kind: "planned", status: "planned" },
  { id: "lantern", name: "Lantern", desc: "Surrealist pixel RPG — earn OMG, find real NFTs in-world", icon: "🕯️", kind: "planned", status: "planned" },
  { id: "addnew", name: "Add App", desc: "Reserve a slot as the ecosystem grows", icon: "+", kind: "add", status: "add" },
];
const loadApps = () => { try { const r = localStorage.getItem(APPS_KEY); if (r) return JSON.parse(r); } catch {} return DEFAULT_APPS; };
const saveApps = (apps) => { try { localStorage.setItem(APPS_KEY, JSON.stringify(apps)); } catch {} };

function TileModal({ app, onClose, onSaveLink }) {
  const [url, setUrl] = useState(app.url || "");
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }} onClick={onClose}>
      <motion.div initial={{ scale: 0.95, y: 10 }} animate={{ scale: 1, y: 0 }} onClick={e => e.stopPropagation()}
        style={{ width: 360, maxWidth: "100%", background: C.bgPanel, border: `1px solid ${C.b1}`, borderRadius: 18, padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, background: "linear-gradient(145deg,#1e3a8a,#0b1330)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.2rem" }}>{app.icon}</div>
            <span style={{ fontSize: "1rem", fontWeight: 700, color: "#fff" }}>{app.name}</span>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: C.textDim }}><XIcon className="w-4 h-4" /></button>
        </div>
        <p style={{ fontSize: "0.8rem", color: C.textMid, lineHeight: 1.6, marginBottom: 16 }}>{app.desc}</p>
        {app.kind === "link" ? (
          <>
            <label style={{ fontSize: "0.65rem", color: C.textDim, textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 6 }}>Connect a URL</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://..." style={{ flex: 1, background: C.bgInput, border: `1px solid ${C.b1}`, borderRadius: 8, padding: "8px 10px", color: C.text, fontSize: "0.78rem" }} />
              <button onClick={() => { onSaveLink(app.id, url); onClose(); }} style={{ padding: "8px 14px", borderRadius: 8, border: "none", background: C.royal, color: "#fff", fontSize: "0.78rem", cursor: "pointer" }}>Save</button>
            </div>
          </>
        ) : (
          <div style={{ fontSize: "0.68rem", color: C.textFaint, fontStyle: "italic" }}>Planned — not wired to a live system yet.</div>
        )}
      </motion.div>
    </motion.div>
  );
}

function AddAppModal({ onClose, onAdd }) {
  const [name, setName] = useState(""); const [icon, setIcon] = useState("⭐"); const [url, setUrl] = useState("");
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }} onClick={onClose}>
      <motion.div initial={{ scale: 0.95, y: 10 }} animate={{ scale: 1, y: 0 }} onClick={e => e.stopPropagation()}
        style={{ width: 340, maxWidth: "100%", background: C.bgPanel, border: `1px solid ${C.b1}`, borderRadius: 18, padding: 24 }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#fff", marginBottom: 14 }}>Reserve a new icon</h3>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="App name" style={{ width: "100%", background: C.bgInput, border: `1px solid ${C.b1}`, borderRadius: 8, padding: "9px 10px", color: C.text, fontSize: "0.8rem", marginBottom: 10 }} />
        <input value={icon} onChange={e => setIcon(e.target.value)} placeholder="Emoji, e.g. 🎮" style={{ width: "100%", background: C.bgInput, border: `1px solid ${C.b1}`, borderRadius: 8, padding: "9px 10px", color: C.text, fontSize: "0.8rem", marginBottom: 10 }} />
        <input value={url} onChange={e => setUrl(e.target.value)} placeholder="URL (optional)" style={{ width: "100%", background: C.bgInput, border: `1px solid ${C.b1}`, borderRadius: 8, padding: "9px 10px", color: C.text, fontSize: "0.8rem", marginBottom: 16 }} />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={onClose} style={{ flex: 1, padding: "9px", borderRadius: 8, border: `1px solid ${C.b1}`, background: "transparent", color: C.textMid, fontSize: "0.78rem", cursor: "pointer" }}>Cancel</button>
          <button onClick={() => name.trim() && onAdd(name.trim(), icon || "⭐", url.trim())} style={{ flex: 1, padding: "9px", borderRadius: 8, border: "none", background: C.royal, color: "#fff", fontSize: "0.78rem", cursor: "pointer" }}>Add</button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function HomeScreen({ profile, onOpenApp, onLock }) {
  const [apps, setApps] = useState(loadApps());
  const [modalApp, setModalApp] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const heroRef = useRef(null);
  const [stars] = useState(() => Array.from({ length: 70 }, () => ({ x: Math.random() * 100, y: Math.random() * 100, s: Math.random() * 2 + 0.5, d: Math.random() * 3 })));

  useEffect(() => saveApps(apps), [apps]);

  const openTile = (app) => {
    if (app.id === "addnew") { setShowAdd(true); return; }
    if (app.kind === "internal") { onOpenApp(app.id); return; }
    if (app.kind === "link" && app.url) { window.open(app.url, "_blank"); return; }
    setModalApp(app);
  };
  const saveLink = (id, url) => setApps(prev => prev.map(a => a.id === id ? { ...a, url } : a));
  const addApp = (name, icon, url) => {
    setApps(prev => {
      const withoutAdd = prev.filter(a => a.id !== "addnew");
      return [...withoutAdd, { id: "custom-" + Date.now(), name, desc: "Custom", icon, kind: url ? "link" : "planned", status: url ? "connect" : "planned", url: url || "" }, prev.find(a => a.id === "addnew")];
    });
    setShowAdd(false);
  };

  return (
    <div ref={heroRef} style={{ position: "relative", minHeight: "100vh", width: "100%", overflow: "hidden",
      background: "radial-gradient(ellipse at 20% 15%, rgba(139,92,246,0.35), transparent 45%), radial-gradient(ellipse at 80% 10%, rgba(16,185,129,0.18), transparent 40%), radial-gradient(ellipse at 50% 100%, rgba(37,99,235,0.35), transparent 50%), #05070f" }}>
      <style>{`
        @keyframes omega-twinkle{0%,100%{opacity:0.15}50%{opacity:0.9}}
        @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
        @keyframes omega-comet{0%{offset-distance:0%;opacity:0}8%{opacity:1}92%{opacity:1}100%{offset-distance:100%;opacity:0}}
        div:hover > .omega-109-mark{color:rgba(255,255,255,0.55)!important}
      `}</style>
      {stars.map((s, i) => (
        <div key={i} style={{ position: "absolute", left: `${s.x}%`, top: `${s.y}%`, width: s.s, height: s.s, borderRadius: "50%", background: "#fff", opacity: 0.7, animation: `omega-twinkle ${2 + s.d}s ease-in-out infinite`, animationDelay: `${s.d}s` }} />
      ))}
      <p style={{ position: "absolute", bottom: 6, left: 10, fontSize: "0.55rem", color: "rgba(255,255,255,0.15)", zIndex: 2 }}>
        placeholder starfield — drop your real photo into HOME_BG_IMAGE
      </p>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 24px", position: "relative", zIndex: 2 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <OmegaLogo size={44} draggable={false} spin />
          <div>
            <div style={{ fontSize: "0.95rem", fontWeight: 800, color: "#fff" }}>Omega Ecosystem</div>
            <div style={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.5)" }}>{profile?.name}</div>
          </div>
        </div>
        <button onClick={onLock} style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 12px", borderRadius: 9, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.7)", fontSize: "0.72rem", cursor: "pointer" }}>
          <LockIcon className="w-3.5 h-3.5" /> Lock
        </button>
      </div>

      <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 30px", position: "relative", zIndex: 2 }}>
        <OmegaLogo size={110} draggable dragConstraintsRef={heroRef} spin />
      </div>

      <div style={{ maxWidth: 880, margin: "0 auto", padding: "0 20px 60px", position: "relative", zIndex: 2, display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 16 }}>
        {apps.map(app => (
          <motion.button key={app.id} onClick={() => openTile(app)} whileHover={{ y: -4 }} whileTap={{ scale: 0.96 }}
            style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, padding: "18px 10px", borderRadius: 18, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", backdropFilter: "blur(6px)", cursor: "pointer", color: "#fff", position: "relative" }}>
            {app.status && app.status !== "add" && (
              <span style={{ position: "absolute", top: 8, right: 8, width: 7, height: 7, borderRadius: "50%", background: app.status === "live" || (app.status === "connect" && app.url) ? "#4ade80" : "#f59e0b" }} />
            )}
            <div style={{ width: 52, height: 52, borderRadius: 14, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.5rem", background: "linear-gradient(145deg,#1e3a8a,#0b1330)", boxShadow: "0 4px 16px rgba(0,0,0,0.4)" }}>{app.icon}</div>
            <div style={{ fontSize: "0.75rem", fontWeight: 600, textAlign: "center" }}>{app.name}</div>
            <div style={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.45)", textAlign: "center", lineHeight: 1.3 }}>{app.desc}</div>
          </motion.button>
        ))}
      </div>

      <AnimatePresence>
        {modalApp && <TileModal app={modalApp} onClose={() => setModalApp(null)} onSaveLink={saveLink} />}
        {showAdd && <AddAppModal onClose={() => setShowAdd(false)} onAdd={addApp} />}
      </AnimatePresence>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// CHAT + AGENT (same components as before, condensed) — real functionality
// ══════════════════════════════════════════════════════════════════════════
function ThinkingBubble({ mode }) {
  const phrases = mode === "standard" ? ["Synthesizing across domains...", "Connecting the threads...", "Going deeper..."] : ["Thinking...", "Processing..."];
  const [phrase] = useState(() => phrases[Math.floor(Math.random() * phrases.length)]);
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: `linear-gradient(135deg,${C.royal},#1d4ed8)`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: `0 0 16px ${C.royalGlow}` }}>
        <span style={{ color: "#fff", fontWeight: 900, fontSize: "1rem" }}>Ω</span>
      </div>
      <div style={{ background: C.bgCard, border: `1px solid ${C.b1}`, borderRadius: 14, borderTopLeftRadius: 2, padding: "11px 16px", boxShadow: "0 2px 12px rgba(0,0,0,0.3)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", gap: 4 }}>
            {[0, 0.18, 0.36].map((delay, i) => (
              <motion.div key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: mode === "standard" ? C.violet : C.royalLt }} animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.15, 0.8] }} transition={{ duration: 1.1, delay, repeat: Infinity }} />
            ))}
          </div>
          <span style={{ fontSize: "0.65rem", color: C.textFaint, fontStyle: "italic" }}>{phrase}</span>
        </div>
      </div>
    </motion.div>
  );
}
function MessageBubble({ message, onSpeak, voiceEnabled }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const handleCopy = () => { navigator.clipboard?.writeText(message.content); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  const formatTime = ts => ts ? new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }} className="group" style={{ display: "flex", alignItems: "flex-start", gap: 10, flexDirection: isUser ? "row-reverse" : "row" }}>
      {isUser ? (
        <div style={{ width: 32, height: 32, borderRadius: 10, background: "linear-gradient(135deg,#1e3a6e,#1d4ed8)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}><UserIcon className="w-4 h-4" style={{ color: "rgba(255,255,255,0.8)" }} /></div>
      ) : (
        <div style={{ width: 36, height: 36, borderRadius: 10, background: `linear-gradient(135deg,${C.royal},#1d4ed8)`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2, boxShadow: `0 0 16px ${C.royalGlow}` }}><span style={{ color: "#fff", fontWeight: 900, fontSize: "1rem", lineHeight: 1 }}>Ω</span></div>
      )}
      <div style={{ display: "flex", flexDirection: "column", maxWidth: "78%", alignItems: isUser ? "flex-end" : "flex-start" }}>
        {!isUser && <div style={{ fontSize: "0.65rem", color: C.accentDim, fontWeight: 500, marginBottom: 4, marginLeft: 2, letterSpacing: "0.05em" }}>Omega</div>}
        <div style={{ padding: "11px 15px", borderRadius: 14, borderTopRightRadius: isUser ? 2 : 14, borderTopLeftRadius: isUser ? 14 : 2, background: isUser ? C.bgUser : C.bgCard, border: `1px solid ${isUser ? "rgba(37,99,235,0.25)" : C.b1}`, boxShadow: "0 2px 12px rgba(0,0,0,0.3)" }}>
          {isUser ? <p style={{ color: C.text, fontSize: "0.875rem", whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.65, margin: 0 }}>{message.content}</p> : <SimpleMarkdown content={message.content} />}
        </div>
        <div className="msg-actions" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, padding: "0 2px", opacity: 0, transition: "opacity 0.15s", flexDirection: isUser ? "row-reverse" : "row" }}>
          <span style={{ fontSize: "0.65rem", color: C.textFaint }}>{formatTime(message.timestamp)}</span>
          <button onClick={handleCopy} style={{ background: "none", border: "none", cursor: "pointer", color: C.textFaint, padding: 0, display: "flex" }}>{copied ? <CheckIcon className="w-3 h-3" style={{ color: "#4ade80" }} /> : <CopyIcon className="w-3 h-3" />}</button>
          {!isUser && voiceEnabled && <button onClick={onSpeak} style={{ background: "none", border: "none", cursor: "pointer", color: C.textFaint, padding: 0, display: "flex" }}><VolumeIcon className="w-3 h-3" /></button>}
        </div>
      </div>
      <style>{`.group:hover .msg-actions{opacity:1!important}`}</style>
    </motion.div>
  );
}
function ModeToggle({ mode, onSetMode, activeDomains, onToggleDomain, voiceName, voiceOptions, onSetVoiceName }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => { const h = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }; document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h); }, []);
  const isDeep = mode === "standard";
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button onClick={() => setOpen(o => !o)} style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 12px", borderRadius: 10, fontSize: "0.72rem", fontWeight: 500, cursor: "pointer", background: isDeep ? "rgba(37,99,235,0.2)" : "rgba(37,99,235,0.08)", border: `1px solid ${isDeep ? "rgba(59,130,246,0.5)" : "rgba(37,99,235,0.2)"}`, color: isDeep ? C.accent : C.textMid }}>
        <BrainIcon className="w-3.5 h-3.5" /><span>{MODELS[mode].label}</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: 6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 6, scale: 0.97 }} style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, width: 300, background: C.bgPanel, border: `1px solid ${C.b1}`, borderRadius: 14, padding: 16, boxShadow: "0 20px 60px rgba(0,0,0,0.8)", zIndex: 50 }}>
            <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
              {Object.entries(MODELS).map(([key, m]) => (
                <button key={key} onClick={() => onSetMode(key)} style={{ flex: 1, padding: "8px 10px", borderRadius: 9, fontSize: "0.75rem", cursor: "pointer", background: mode === key ? C.royal : "rgba(37,99,235,0.08)", border: `1px solid ${mode === key ? C.royalLt : "rgba(37,99,235,0.2)"}`, color: mode === key ? "#fff" : C.textMid, textAlign: "left" }}>
                  <div style={{ fontWeight: 600 }}>{m.label}</div><div style={{ fontSize: "0.65rem", opacity: 0.7 }}>{m.desc}</div>
                </button>
              ))}
            </div>
            <div style={{ fontSize: "0.65rem", color: C.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Active Domains</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: 14 }}>
              {DOMAINS.map(({ key, Icon: I, label, color }) => (
                <button key={key} onClick={() => onToggleDomain(key)} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 10px", borderRadius: 8, cursor: "pointer", background: activeDomains.includes(key) ? "rgba(37,99,235,0.14)" : "transparent", border: `1px solid ${activeDomains.includes(key) ? C.b2 : "transparent"}`, color: activeDomains.includes(key) ? "#fff" : C.textDim }}>
                  <I className="w-3.5 h-3.5" style={{ color: activeDomains.includes(key) ? color : C.textFaint }} /><span style={{ flex: 1, textAlign: "left", fontSize: "0.78rem" }}>{label}</span>{activeDomains.includes(key) && <CheckIcon className="w-3 h-3" style={{ color: C.royalLt }} />}
                </button>
              ))}
            </div>
            {voiceOptions?.length > 0 && (
              <>
                <div style={{ fontSize: "0.65rem", color: C.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Voice</div>
                <select value={voiceName || ""} onChange={e => onSetVoiceName(e.target.value)} style={{ width: "100%", background: C.bgInput, color: C.text, border: `1px solid ${C.b1}`, borderRadius: 8, padding: "7px 8px", fontSize: "0.75rem" }}>
                  {voiceOptions.map(v => <option key={v.name} value={v.name}>{v.name}</option>)}
                </select>
                <p style={{ fontSize: "0.6rem", color: C.textFaint, marginTop: 6, lineHeight: 1.4 }}>System voices only — browsers can't access proprietary voices like ChatGPT's.</p>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
function ChatHeader({ onToggleSidebar, onGoHome, voiceEnabled, onToggleVoice, onStopSpeech, mode, onSetMode, activeDomains, onToggleDomain, voiceName, voiceOptions, onSetVoiceName }) {
  const [stopped, setStopped] = useState(false);
  const isDeep = mode === "standard";
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", background: isDeep ? `linear-gradient(90deg,rgba(20,10,50,0.95),${C.bg},rgba(10,15,50,0.95))` : C.bg, borderBottom: `1px solid ${isDeep ? "rgba(59,130,246,0.25)" : C.b1}`, flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button onClick={onToggleSidebar} style={{ background: "none", border: "none", cursor: "pointer", color: C.textMid, display: "flex", padding: 0 }}><MenuIcon className="w-5 h-5" /></button>
        <button onClick={onGoHome} style={{ background: "none", border: "none", cursor: "pointer", color: C.textMid, display: "flex", padding: 0 }} title="Home"><HomeIcon className="w-4.5 h-4.5" /></button>
        <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
          <div style={{ position: "relative", flexShrink: 0 }}>
            <div style={{ width: 32, height: 32, borderRadius: 10, background: `linear-gradient(135deg,${C.royal},#1d4ed8)`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 0 14px ${C.royalGlow}` }}><span style={{ color: "#fff", fontWeight: 900, fontSize: "0.95rem" }}>Ω</span></div>
            <div style={{ position: "absolute", bottom: -2, right: -2, width: 10, height: 10, borderRadius: "50%", background: isDeep ? C.violet : "#4ade80", border: `2px solid ${C.bg}` }} />
          </div>
          <div>
            <span style={{ fontSize: "0.875rem", fontWeight: 700, color: isDeep ? C.accent : "#fff" }}>Omega</span>
            <div style={{ fontSize: "0.65rem", color: C.textDim }}>{isDeep ? "Deep · full depth" : "Fast · unlimited"}</div>
          </div>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <ModeToggle mode={mode} onSetMode={onSetMode} activeDomains={activeDomains} onToggleDomain={onToggleDomain} voiceName={voiceName} voiceOptions={voiceOptions} onSetVoiceName={onSetVoiceName} />
        {voiceEnabled && <button onClick={() => { onStopSpeech(); setStopped(true); setTimeout(() => setStopped(false), 1000); }} style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 10px", borderRadius: 8, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)", color: "#f87171", fontSize: "0.72rem", cursor: "pointer" }}><SquareIcon className="w-3 h-3" /><span>{stopped ? "Stopped" : "Stop"}</span></button>}
        <button onClick={onToggleVoice} style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 12px", borderRadius: 8, fontSize: "0.72rem", cursor: "pointer", background: voiceEnabled ? "rgba(37,99,235,0.15)" : "rgba(37,99,235,0.06)", border: `1px solid ${voiceEnabled ? "rgba(59,130,246,0.4)" : "rgba(37,99,235,0.15)"}`, color: voiceEnabled ? C.accent : C.textMid }}>{voiceEnabled ? <VolumeIcon className="w-3.5 h-3.5" /> : <VolumeXIcon className="w-3.5 h-3.5" />}</button>
      </div>
    </div>
  );
}
function ChatInput({ onSend, isThinking }) {
  const [value, setValue] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const textareaRef = useRef(null); const recRef = useRef(null); const timerRef = useRef(null);
  useEffect(() => { if (textareaRef.current) { textareaRef.current.style.height = "auto"; textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 180) + "px"; } }, [value]);
  const submit = () => { if (!value.trim() || isThinking) return; onSend(value.trim()); setValue(""); if (textareaRef.current) textareaRef.current.style.height = "auto"; };
  const startRec = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SR) return;
    const r = new SR(); r.continuous = true; r.interimResults = true; r.lang = "en-US";
    r.onresult = e => { let t = ""; for (let i = e.resultIndex; i < e.results.length; i++) t += e.results[i][0].transcript; setValue(t); };
    r.onerror = stopRec; r.onend = () => { setIsRecording(false); clearInterval(timerRef.current); };
    r.start(); recRef.current = r; setIsRecording(true); setRecordingTime(0);
    timerRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000);
  };
  const stopRec = () => { recRef.current?.stop(); recRef.current = null; setIsRecording(false); clearInterval(timerRef.current); };
  const fmt = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  return (
    <div style={{ padding: "14px 16px", background: C.bg, borderTop: `1px solid ${C.b1}`, flexShrink: 0 }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <AnimatePresence>{isRecording && <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, paddingLeft: 4, fontSize: "0.72rem", color: "#f87171" }}><motion.div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} animate={{ opacity: [1, 0] }} transition={{ duration: 0.8, repeat: Infinity }} />Recording · {fmt(recordingTime)}</motion.div>}</AnimatePresence>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 10, padding: "10px 14px", borderRadius: 16, background: isRecording ? "rgba(50,10,10,0.8)" : C.bgInput, border: `1px solid ${isRecording ? "rgba(239,68,68,0.4)" : "rgba(37,99,235,0.25)"}`, boxShadow: "0 4px 24px rgba(0,0,0,0.4)" }}>
          <textarea ref={textareaRef} value={value} onChange={e => setValue(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} placeholder={isRecording ? "Listening..." : "Message Omega..."} rows={1} disabled={isThinking} style={{ flex: 1, background: "transparent", color: C.text, fontSize: "0.875rem", outline: "none", resize: "none", lineHeight: 1.6, minHeight: 24, maxHeight: 180, border: "none", fontFamily: "inherit" }} />
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0, paddingBottom: 2 }}>
            <button onClick={isRecording ? stopRec : startRec} disabled={isThinking} style={{ width: 32, height: 32, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", border: "none", background: isRecording ? "#ef4444" : "rgba(37,99,235,0.15)", color: isRecording ? "#fff" : C.textMid, opacity: isThinking ? 0.4 : 1 }}>{isRecording ? <SquareIcon className="w-3.5 h-3.5" /> : <MicIcon className="w-3.5 h-3.5" />}</button>
            <button onClick={submit} disabled={!value.trim() || isThinking} style={{ width: 32, height: 32, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", cursor: value.trim() && !isThinking ? "pointer" : "not-allowed", border: "none", background: value.trim() && !isThinking ? C.royal : "rgba(37,99,235,0.12)", color: value.trim() && !isThinking ? "#fff" : C.textFaint }}>{isThinking ? <LoaderIcon className="w-3.5 h-3.5" /> : <SendIcon className="w-3.5 h-3.5" />}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
function AgentThoughtBox({ latestLine, status }) {
  const [minimized, setMinimized] = useState(false);
  if (!latestLine) return null;
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} style={{ position: "fixed", bottom: 18, right: 18, zIndex: 40, width: minimized ? 44 : 280, background: C.bgPanel, border: `1px solid ${C.b2}`, borderRadius: 14, boxShadow: "0 10px 40px rgba(0,0,0,0.6)", overflow: "hidden" }}>
      <div onClick={() => setMinimized(m => !m)} style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", cursor: "pointer", borderBottom: minimized ? "none" : `1px solid ${C.b1}` }}>
        <motion.div style={{ width: 7, height: 7, borderRadius: "50%", background: status === "error" ? C.red : status === "done" ? C.emerald : C.royalLt, flexShrink: 0 }} animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 1.4, repeat: Infinity }} />
        {!minimized && <span style={{ fontSize: "0.68rem", color: C.textDim, textTransform: "uppercase", letterSpacing: "0.08em", flex: 1 }}>Agent thinking</span>}
      </div>
      {!minimized && <div style={{ padding: "10px 12px", fontSize: "0.72rem", color: C.text, lineHeight: 1.5, fontFamily: "monospace" }}>{latestLine}</div>}
    </motion.div>
  );
}
function AgentConsole({ baseUrl, onTaskUpdate, tasks }) {
  const [taskText, setTaskText] = useState("Check Oracle score, find failing component, propose fix");
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [log, setLog] = useState([]);
  const [running, setRunning] = useState(false);
  const pollRef = useRef(null);
  const appendLog = (text, kind = "info") => setLog(prev => [...prev, { time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }), text, kind }]);
  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  useEffect(() => () => stopPolling(), []);
  const runTask = async () => {
    if (!taskText.trim() || running) return;
    setRunning(true);
    appendLog(`→ POST /agent/run { task: "${taskText.trim()}" }`, "cmd");
    try {
      const res = await fetch(`${baseUrl.replace(/\/$/, "")}/agent/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task: taskText.trim() }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setActiveTaskId(data.task_id);
      appendLog(`← task_id ${data.task_id} · status: ${data.status}`, "ok");
      onTaskUpdate({ task_id: data.task_id, task: taskText.trim(), status: data.status, result: null });
      pollRef.current = setInterval(async () => {
        try {
          const tRes = await fetch(`${baseUrl.replace(/\/$/, "")}/agent/trace`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task_id: data.task_id }) });
          if (!tRes.ok) throw new Error(`HTTP ${tRes.status}`);
          const trace = await tRes.json();
          appendLog(`status: ${trace.status}${trace.result ? ` · result: ${trace.result}` : ""}`, trace.status === "error" ? "error" : "poll");
          onTaskUpdate({ task_id: data.task_id, task: taskText.trim(), status: trace.status, result: trace.result });
          if (["done", "error", "max_steps_reached"].includes(trace.status)) { stopPolling(); setRunning(false); }
        } catch (e) { appendLog(`trace poll failed: ${e.message} — check CORS / base URL`, "error"); stopPolling(); setRunning(false); }
      }, 2000);
    } catch (e) { appendLog(`/agent/run failed: ${e.message} — check CORS / base URL`, "error"); setRunning(false); }
  };
  const latestStatus = tasks.find(t => t.task_id === activeTaskId)?.status;
  const latestLine = log.length > 0 ? log[log.length - 1].text : null;
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: C.bg }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", borderBottom: `1px solid ${C.b1}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 10, background: `linear-gradient(135deg,${C.royal},#1d4ed8)`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 0 14px ${C.royalGlow}` }}><TerminalIcon className="w-4 h-4" style={{ color: "#fff" }} /></div>
          <div><div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#fff" }}>Omega Agent — Console</div><div style={{ fontSize: "0.65rem", color: C.textDim }}>{baseUrl}</div></div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 10px", borderRadius: 8, background: "rgba(37,99,235,0.06)", border: `1px solid ${C.b1}`, fontSize: "0.65rem", color: C.textFaint, fontFamily: "monospace" }}><ActivityIcon className="w-3 h-3" /> {running ? "running" : "idle"}</div>
      </div>
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "260px 1fr 220px", overflow: "hidden" }}>
        <div style={{ padding: 16, borderRight: `1px solid ${C.b1}`, overflowY: "auto" }}>
          <div style={{ fontSize: "0.62rem", color: C.textFaint, textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 8 }}>New Task</div>
          <div style={{ background: C.bgInput, border: `1px solid ${C.b1}`, borderRadius: 12, padding: 10, marginBottom: 12 }}>
            <textarea value={taskText} onChange={e => setTaskText(e.target.value)} rows={4} style={{ width: "100%", background: "transparent", border: "none", outline: "none", color: C.text, fontSize: "0.8rem", resize: "none", fontFamily: "inherit" }} />
          </div>
          <button onClick={runTask} disabled={running || !taskText.trim()} style={{ width: "100%", padding: "10px", borderRadius: 10, border: "none", cursor: running ? "not-allowed" : "pointer", background: running ? "rgba(37,99,235,0.2)" : C.royal, color: "#fff", fontSize: "0.8rem", fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>{running ? <LoaderIcon className="w-3.5 h-3.5" /> : <SendIcon className="w-3.5 h-3.5" />}{running ? "Running..." : "Run task"}</button>
          <div style={{ fontSize: "0.62rem", color: C.textFaint, textTransform: "uppercase", letterSpacing: "0.12em", margin: "20px 0 8px" }}>Recent tasks</div>
          {tasks.slice().reverse().map(t => (<div key={t.task_id} style={{ padding: "8px 0", borderBottom: `1px solid ${C.b1}` }}><div style={{ fontSize: "0.75rem", color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.task}</div><div style={{ fontSize: "0.62rem", color: t.status === "done" ? C.emerald : t.status === "error" ? "#f87171" : C.accent }}>{t.status}</div></div>))}
        </div>
        <div style={{ padding: 16, overflowY: "auto" }}>
          <div style={{ fontSize: "0.62rem", color: C.textFaint, textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 8 }}>Live Trace</div>
          {log.map((l, i) => (<div key={i} style={{ display: "grid", gridTemplateColumns: "70px 1fr", gap: 10, padding: "8px 0", borderBottom: `1px solid ${C.b1}`, fontSize: "0.78rem" }}><div style={{ color: C.textFaint, fontSize: "0.68rem" }}>{l.time}</div><div style={{ color: l.kind === "error" ? "#f87171" : l.kind === "ok" ? C.emerald : l.kind === "cmd" ? C.accent : C.text, fontFamily: "monospace", wordBreak: "break-word" }}>{l.text}</div></div>))}
        </div>
        <div style={{ padding: 16, borderLeft: `1px solid ${C.b1}`, background: C.bgPanel, overflowY: "auto" }}>
          <div style={{ fontSize: "0.62rem", color: C.textFaint, textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 4 }}>Sandbox — /home</div>
          <div style={{ fontSize: "0.62rem", color: C.textFaint, marginBottom: 12, fontStyle: "italic" }}>Static preview — no live file-state endpoint yet.</div>
          {[{ icon: <FolderIcon className="w-3.5 h-3.5" />, label: "omega_workspace/" }, { icon: <ServerIcon className="w-3.5 h-3.5" />, label: "omega_brain.py", tag: "8095" }, { icon: <ServerIcon className="w-3.5 h-3.5" />, label: "omega_agent.py" }].map((n, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", fontSize: "0.75rem", color: C.textMid }}>{n.icon}<span style={{ flex: 1 }}>{n.label}</span>{n.tag && <span style={{ fontSize: "0.6rem", color: C.accent, border: `1px solid ${C.b1}`, borderRadius: 4, padding: "1px 5px" }}>{n.tag}</span>}</div>
          ))}
        </div>
      </div>
      <AgentThoughtBox latestLine={latestLine} status={latestStatus} />
    </div>
  );
}
function Sidebar({ open, onClose, activeTab, onGoHome, onSetTab, conversations, activeConvId, onSelectConv, onNewConv, onDeleteConv, memory, onExportMemory, profile, agentTasks, baseUrl, onSetBaseUrl }) {
  const personality = memory.personality_traits;
  return (
    <>
      <AnimatePresence>{open && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 20 }} />}</AnimatePresence>
      <div style={{ position: "fixed", top: 0, left: 0, height: "100%", zIndex: 30, width: 280, background: C.bgSide, borderRight: `1px solid ${C.b1}`, display: "flex", flexDirection: "column", transform: open ? "translateX(0)" : "translateX(-100%)", transition: "transform 0.3s ease" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px", borderBottom: `1px solid ${C.b1}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: 8, background: `linear-gradient(135deg,${C.royal},#1d4ed8)`, display: "flex", alignItems: "center", justifyContent: "center" }}><span style={{ color: "#fff", fontWeight: 900, fontSize: "0.75rem" }}>Ω</span></div>
            <div><div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#fff" }}>Omega</div><div style={{ fontSize: "0.62rem", color: C.accentDim }}>by Thomas Lee Harvey</div></div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: C.textDim, display: "flex", padding: 0 }}><XIcon className="w-4 h-4" /></button>
        </div>
        <div style={{ display: "flex", gap: 6, padding: "12px" }}>
          <button onClick={onGoHome} style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "8px 6px", borderRadius: 10, fontSize: "0.72rem", cursor: "pointer", background: "rgba(37,99,235,0.08)", border: `1px solid ${C.b1}`, color: C.textMid }}><HomeIcon className="w-3.5 h-3.5" /> Home</button>
          <button onClick={() => onSetTab("chat")} style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "8px 6px", borderRadius: 10, fontSize: "0.72rem", cursor: "pointer", background: activeTab === "chat" ? C.royal : "rgba(37,99,235,0.08)", border: `1px solid ${activeTab === "chat" ? C.royalLt : C.b1}`, color: activeTab === "chat" ? "#fff" : C.textMid }}><MsgIcon className="w-3.5 h-3.5" /> Chat</button>
          <button onClick={() => onSetTab("agent")} style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "8px 6px", borderRadius: 10, fontSize: "0.72rem", cursor: "pointer", background: activeTab === "agent" ? C.royal : "rgba(37,99,235,0.08)", border: `1px solid ${activeTab === "agent" ? C.royalLt : C.b1}`, color: activeTab === "agent" ? "#fff" : C.textMid }}><TerminalIcon className="w-3.5 h-3.5" /> Agent</button>
        </div>
        {activeTab === "chat" ? (
          <>
            <div style={{ padding: "0 12px 10px" }}><button onClick={onNewConv} style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 10, border: `1px solid ${C.b1}`, fontSize: "0.8rem", color: C.textMid, cursor: "pointer", background: "transparent" }}><PlusIcon className="w-4 h-4" /> New conversation</button></div>
            <div style={{ flex: 1, overflowY: "auto", padding: "0 12px 16px" }}>
              <div style={{ fontSize: "0.62rem", color: C.textFaint, textTransform: "uppercase", letterSpacing: "0.12em", padding: "8px 4px" }}>Threads</div>
              {conversations.map(conv => (
                <div key={conv.id} onClick={() => onSelectConv(conv.id)} className="conv-item" style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 10, cursor: "pointer", marginBottom: 2, background: conv.id === activeConvId ? "rgba(37,99,235,0.18)" : "transparent", border: `1px solid ${conv.id === activeConvId ? C.b2 : "transparent"}`, color: conv.id === activeConvId ? "#fff" : C.textMid }}>
                  <MsgIcon className="w-3.5 h-3.5" style={{ flexShrink: 0, opacity: 0.6 }} /><span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: "0.8rem" }}>{conv.title}</span>
                  <button onClick={e => { e.stopPropagation(); onDeleteConv(conv.id); }} className="del-btn" style={{ background: "none", border: "none", cursor: "pointer", color: C.textFaint, padding: 0, display: "flex", opacity: 0 }}><TrashIcon className="w-3 h-3" /></button>
                </div>
              ))}
              <style>{`.conv-item:hover{background:rgba(37,99,235,0.10)!important;color:#fff!important}.conv-item:hover .del-btn{opacity:1!important}`}</style>
            </div>
            <div style={{ margin: "0 12px 8px", padding: 12, borderRadius: 12, background: "rgba(37,99,235,0.07)", border: `1px solid ${C.b1}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}><BrainIcon className="w-3.5 h-3.5" style={{ color: C.accent }} /><span style={{ fontSize: "0.65rem", color: C.textDim, textTransform: "uppercase" }}>Omega's Growth</span></div>
              {[{ label: "Curiosity", val: personality.curiosity, from: C.royalLt, to: "#93c5fd" }, { label: "Philosophy", val: personality.philosophy, from: C.violet, to: "#c4b5fd" }, { label: "Engineering", val: personality.engineering, from: "#10b981", to: "#6ee7b7" }].map(({ label, val, from, to }) => (
                <div key={label} style={{ marginBottom: 7 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", color: C.textDim, marginBottom: 3 }}><span>{label}</span><span>{Math.round(val * 100)}%</span></div>
                  <div style={{ height: 4, background: "rgba(37,99,235,0.12)", borderRadius: 9999, overflow: "hidden" }}><motion.div style={{ height: "100%", borderRadius: 9999, background: `linear-gradient(90deg,${from},${to})` }} initial={{ width: 0 }} animate={{ width: `${val * 100}%` }} transition={{ duration: 1, ease: "easeOut" }} /></div>
                </div>
              ))}
              <div style={{ marginTop: 8, fontSize: "0.62rem", color: C.textFaint }}>{memory.interaction_count} exchanges</div>
            </div>
            <div style={{ padding: "0 12px 12px" }}><button onClick={onExportMemory} style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "7px 12px", borderRadius: 9, border: "1px solid rgba(139,92,246,0.25)", fontSize: "0.72rem", color: C.violet, cursor: "pointer", background: "rgba(139,92,246,0.05)" }}><SaveIcon className="w-3 h-3" /> Export Memory</button></div>
          </>
        ) : (
          <div style={{ flex: 1, overflowY: "auto", padding: "0 12px 16px" }}>
            <div style={{ fontSize: "0.62rem", color: C.textFaint, textTransform: "uppercase", letterSpacing: "0.12em", padding: "8px 4px" }}>Brain endpoint</div>
            <div style={{ background: C.bgInput, border: `1px solid ${C.b1}`, borderRadius: 10, padding: "8px 10px", marginBottom: 14 }}><input value={baseUrl} onChange={e => onSetBaseUrl(e.target.value)} placeholder="http://localhost:8095" style={{ width: "100%", background: "transparent", border: "none", outline: "none", color: C.text, fontSize: "0.75rem", fontFamily: "monospace" }} /></div>
            <div style={{ fontSize: "0.62rem", color: C.textFaint, textTransform: "uppercase", letterSpacing: "0.12em", padding: "8px 4px" }}>Recent tasks</div>
            {agentTasks.length === 0 && <div style={{ fontSize: "0.72rem", color: C.textFaint, padding: "4px" }}>No tasks run yet this session.</div>}
            {agentTasks.map(t => (<div key={t.task_id} style={{ padding: "8px 10px", borderRadius: 8, marginBottom: 4, background: "rgba(37,99,235,0.05)", border: `1px solid ${C.b1}` }}><div style={{ fontSize: "0.75rem", color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.task}</div><div style={{ fontSize: "0.62rem", color: t.status === "done" ? C.emerald : t.status === "error" ? "#f87171" : C.accent }}>{t.status}</div></div>))}
          </div>
        )}
        <div style={{ padding: "10px 16px 14px", borderTop: `1px solid ${C.b1}` }}>
          {profile && <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}><div style={{ width: 22, height: 22, borderRadius: 6, background: "rgba(37,99,235,0.15)", display: "flex", alignItems: "center", justifyContent: "center" }}><UserIcon className="w-3 h-3" style={{ color: C.accent }} /></div><div style={{ minWidth: 0 }}><div style={{ fontSize: "0.7rem", color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{profile.name}</div></div></div>}
          <div style={{ fontSize: "0.6rem", color: C.textFaint, lineHeight: 1.6, textAlign: "center" }}>Omega Ecosystem<br /><span style={{ color: "rgba(255,255,255,0.2)" }}>Built on two Android phones in Termux</span></div>
        </div>
      </div>
    </>
  );
}
function WelcomeScreen({ onPrompt, profile }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-start", minHeight: "100%", padding: "48px 16px 60px", background: C.bg }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", maxWidth: 640, width: "100%" }}>
        <div style={{ marginBottom: 16 }}><OmegaLogo size={80} spin /></div>
        <h1 style={{ fontSize: "1.7rem", fontWeight: 900, color: "#fff", marginBottom: 6, textAlign: "center" }}>{profile?.name ? `Good to see you, ${profile.name.split(" ")[0]}` : "I am Omega"}</h1>
        <p style={{ fontSize: "0.85rem", color: C.textDim, textAlign: "center", marginBottom: 32, maxWidth: 460, lineHeight: 1.6 }}>Built by Thomas Lee Harvey. Ask anything.</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, width: "100%" }}>
          {STARTERS.map((s, i) => (<button key={i} onClick={() => onPrompt(s.label)} style={{ textAlign: "left", padding: "14px 16px", borderRadius: 14, background: "rgba(37,99,235,0.06)", border: `1px solid ${C.b1}`, color: C.text, fontSize: "0.8rem", cursor: "pointer", display: "flex", gap: 10, alignItems: "flex-start" }}><span style={{ fontSize: "1.1rem" }}>{s.icon}</span><span>{s.label}</span></button>))}
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// APP SHELL — Chat + Agent, reached from Home
// ══════════════════════════════════════════════════════════════════════════
function AppShell({ view, setView, onGoHome, profile }) {
  const saved = loadState();
  const [conversations, setConversations] = useState(saved?.conversations || [{ id: mkId(), title: "New conversation", messages: [] }]);
  const [activeConvId, setActiveConvId] = useState(saved?.activeConvId || null);
  const [isThinking, setIsThinking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceName, setVoiceName] = useState(saved?.voiceName || null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mode, setMode] = useState(saved?.mode || "standard");
  const [activeDomains, setActiveDomains] = useState(saved?.activeDomains || ["consciousness", "physics", "engineering", "creativity", "fintech", "philosophy"]);
  const [memory, setMemory] = useState(saved?.memory || DEFAULT_MEMORY);
  const [baseUrl, setBaseUrl] = useState(saved?.baseUrl || "http://localhost:8095");
  const [agentTasks, setAgentTasks] = useState([]);
  const endRef = useRef(null);
  const voicesRef = useRef([]);
  const [voiceOptions, setVoiceOptions] = useState([]);

  useEffect(() => { if (!activeConvId && conversations.length > 0) setActiveConvId(conversations[0].id); }, []);
  useEffect(() => {
    const load = () => {
      const v = window.speechSynthesis?.getVoices() || [];
      if (v.length) {
        voicesRef.current = v;
        const preferred = ["Samantha", "Ava", "Aria", "Jenny", "Zira", "Victoria", "Karen", "Google US English", "Google UK English Female"];
        const ranked = [...v].sort((a, b) => { const ai = preferred.findIndex(n => a.name.toLowerCase().includes(n.toLowerCase())); const bi = preferred.findIndex(n => b.name.toLowerCase().includes(n.toLowerCase())); return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi); });
        setVoiceOptions(ranked.filter(vo => vo.lang?.startsWith("en")));
        if (!voiceName && ranked.length) setVoiceName(ranked[0].name);
      }
    };
    load(); window.speechSynthesis?.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis?.removeEventListener("voiceschanged", load);
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [conversations, isThinking]);
  useEffect(() => { saveState({ conversations, activeConvId, mode, activeDomains, memory, voiceName, baseUrl }); }, [conversations, activeConvId, mode, activeDomains, memory, voiceName, baseUrl]);

  const activeConv = conversations.find(c => c.id === activeConvId);
  const messages = activeConv?.messages || [];

  const speakText = useCallback(text => {
    if (!voiceEnabled) return;
    window.speechSynthesis?.cancel();
    const utter = new window.SpeechSynthesisUtterance(text.replace(/[*_#`~═─]/g, "").trim());
    const voices = voicesRef.current.length > 0 ? voicesRef.current : window.speechSynthesis?.getVoices() || [];
    const chosen = voices.find(v => v.name === voiceName) || voices.find(v => v.lang?.startsWith("en")) || voices[0];
    if (chosen) utter.voice = chosen;
    utter.rate = 0.98; utter.pitch = 1.02;
    window.speechSynthesis?.speak(utter);
  }, [voiceEnabled, voiceName]);
  const stopSpeech = () => window.speechSynthesis?.cancel();

  const sendMessage = useCallback(async content => {
    if (!content.trim() || isThinking || !activeConvId) return;
    const now = new Date().toISOString();
    const userMsg = { role: "user", content, timestamp: now };
    const updatedMsgs = [...messages, userMsg];
    const title = messages.length === 0 ? content.slice(0, 52) + (content.length > 52 ? "…" : "") : undefined;
    setConversations(prev => prev.map(c => c.id === activeConvId ? { ...c, messages: updatedMsgs, ...(title ? { title } : {}) } : c));
    setIsThinking(true);
    const history = compressHistory(updatedMsgs);
    const systemPrompt = buildSystemPrompt(mode, activeDomains, memory, profile);
    const model = MODELS[mode];
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model: model.id, max_tokens: model.tokens, messages: [{ role: "user", content: `${systemPrompt}\n\nCONVERSATION:\n${history}\n\nRespond as Omega now.` }] }) });
      const data = await res.json();
      const result = data.content?.map(b => b.text || "").join("") || "My signal flickered. Try again.";
      const aiMsg = { role: "assistant", content: result, timestamp: new Date().toISOString() };
      setConversations(prev => prev.map(c => c.id === activeConvId ? { ...c, messages: [...updatedMsgs, aiMsg] } : c));
      setMemory(prev => { const t = { ...prev.personality_traits }; t.curiosity = Math.min(1, t.curiosity + 0.003); t.philosophy = Math.min(1, t.philosophy + 0.002); t.engineering = Math.min(1, t.engineering + 0.002); return { ...prev, interaction_count: prev.interaction_count + 1, personality_traits: t }; });
      speakText(result);
    } catch (err) {
      const errMsg = { role: "assistant", content: "Signal lost. Try again.", timestamp: new Date().toISOString() };
      setConversations(prev => prev.map(c => c.id === activeConvId ? { ...c, messages: [...updatedMsgs, errMsg] } : c));
    } finally { setIsThinking(false); }
  }, [messages, activeConvId, isThinking, memory, mode, activeDomains, speakText, profile]);

  const newConv = () => { const c = { id: mkId(), title: "New conversation", messages: [] }; setConversations(p => [c, ...p]); setActiveConvId(c.id); setSidebarOpen(false); };
  const delConv = id => setConversations(prev => { const f = prev.filter(c => c.id !== id); if (f.length === 0) { const fb = { id: mkId(), title: "New conversation", messages: [] }; setActiveConvId(fb.id); return [fb]; } if (id === activeConvId) setActiveConvId(f[0].id); return f; });
  const toggleDomain = key => setActiveDomains(p => p.includes(key) ? p.filter(d => d !== key) : [...p, key]);
  const exportMemory = () => {
    const data = JSON.stringify({ memory, conversations: conversations.map(c => ({ title: c.title, messageCount: c.messages.length })) }, null, 2);
    const blob = new Blob([data], { type: "application/json" }); const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "omega_memory.json"; a.click(); URL.revokeObjectURL(url);
  };
  const onTaskUpdate = (t) => setAgentTasks(prev => { const idx = prev.findIndex(p => p.task_id === t.task_id); if (idx === -1) return [...prev, t]; const copy = [...prev]; copy[idx] = { ...copy[idx], ...t }; return copy; });

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", overflow: "hidden", background: C.bg, color: C.text, fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" }}>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} activeTab={view} onGoHome={onGoHome} onSetTab={t => { setView(t); setSidebarOpen(false); }} conversations={conversations} activeConvId={activeConvId} onSelectConv={id => { setActiveConvId(id); setSidebarOpen(false); }} onNewConv={newConv} onDeleteConv={delConv} memory={memory} onExportMemory={exportMemory} profile={profile} agentTasks={agentTasks} baseUrl={baseUrl} onSetBaseUrl={setBaseUrl} />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0, height: "100%" }}>
        {view === "chat" ? (
          <>
            <ChatHeader onToggleSidebar={() => setSidebarOpen(o => !o)} onGoHome={onGoHome} voiceEnabled={voiceEnabled} onToggleVoice={() => { setVoiceEnabled(v => !v); if (voiceEnabled) stopSpeech(); }} onStopSpeech={stopSpeech} mode={mode} onSetMode={setMode} activeDomains={activeDomains} onToggleDomain={toggleDomain} voiceName={voiceName} voiceOptions={voiceOptions} onSetVoiceName={setVoiceName} />
            <div style={{ flex: 1, overflowY: "auto", background: C.bg }}>
              {messages.length === 0 ? <WelcomeScreen onPrompt={sendMessage} profile={profile} /> : (
                <div style={{ maxWidth: 720, margin: "0 auto", padding: "24px 16px", display: "flex", flexDirection: "column", gap: 20 }}>
                  <AnimatePresence initial={false}>{messages.map((msg, i) => (<MessageBubble key={i} message={msg} voiceEnabled={voiceEnabled} onSpeak={() => speakText(msg.content)} />))}</AnimatePresence>
                  <AnimatePresence>{isThinking && <ThinkingBubble mode={mode} />}</AnimatePresence>
                  <div ref={endRef} />
                </div>
              )}
            </div>
            <ChatInput onSend={sendMessage} isThinking={isThinking} />
          </>
        ) : (
          <AgentConsole baseUrl={baseUrl} onTaskUpdate={onTaskUpdate} tasks={agentTasks} />
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// ROOT
// ══════════════════════════════════════════════════════════════════════════
export default function OmegaEcosystemApp() {
  const [profile, setProfile] = useState(null);
  const [unlocked, setUnlocked] = useState(false);
  const [view, setView] = useState("home");

  const handleUnlocked = (p) => { setProfile(p); setUnlocked(true); };
  const handleLock = () => { setUnlocked(false); setView("home"); };

  return (
    <div style={{ fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" }}>
      <style>{`
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:rgba(37,99,235,0.3);border-radius:9999px}
      `}</style>
      {!unlocked ? (
        <VaultGate onUnlocked={handleUnlocked} />
      ) : view === "home" ? (
        <HomeScreen profile={profile} onOpenApp={setView} onLock={handleLock} />
      ) : view === "gallery" ? (
        <GalleryView onGoHome={() => setView("home")} />
      ) : (
        <AppShell view={view} setView={setView} onGoHome={() => setView("home")} profile={profile} />
      )}
    </div>
  );
}

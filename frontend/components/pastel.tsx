"use client";

import Link from "next/link";
import { ReactNode, useRef } from "react";

export function BrandMark({ href = "/", className = "" }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={`relative z-20 inline-flex items-center gap-2 ${className}`}>
      <span
        className="grid place-items-center"
        style={{ width: 28, height: 28, borderRadius: 9, background: "#c9b8f0" }}
      >
        <span style={{ width: 9, height: 9, background: "#7c5fc4", borderRadius: 3, display: "block" }} />
      </span>
      <span className="font-display" style={{ fontSize: 18, color: "#4a3f66" }}>
        Atelier
      </span>
    </Link>
  );
}

export function PastelBackdrop({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen" style={{ background: "#f3eef9", color: "#3d3453" }}>
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
        <div style={{ position: "absolute", width: 520, height: 520, borderRadius: "50%", background: "#c9b8f0", opacity: 0.7, top: -160, left: -140 }} />
        <div style={{ position: "absolute", width: 420, height: 420, borderRadius: "50%", background: "#a7e3d0", opacity: 0.7, bottom: -140, left: -80 }} />
        <div style={{ position: "absolute", width: 460, height: 460, borderRadius: "50%", background: "#ffd3b0", opacity: 0.65, bottom: -160, right: -120 }} />
        <div style={{ position: "absolute", width: 280, height: 280, borderRadius: "50%", background: "#ffc2d8", opacity: 0.6, top: -80, right: -50 }} />
        <div style={{ position: "absolute", width: 46, height: 46, borderRadius: 14, background: "#fff", opacity: 0.9, top: 64, right: 110, transform: "rotate(18deg)", boxShadow: "0 14px 24px rgba(160,120,220,0.25)" }} />
        <div style={{ position: "absolute", width: 26, height: 26, borderRadius: "50%", background: "#ffb6c9", top: 130, right: 70, boxShadow: "0 8px 16px rgba(255,150,180,0.35)" }} />
        <div style={{ position: "absolute", width: 60, height: 60, borderRadius: "50%", border: "6px solid #fff", opacity: 0.75, bottom: 90, left: 70 }} />
        <div style={{ position: "absolute", width: 30, height: 30, borderRadius: 9, background: "#bdeedd", bottom: 150, left: 130, transform: "rotate(-12deg)", boxShadow: "0 10px 18px rgba(120,200,170,0.3)" }} />
      </div>
      <div className="relative z-10">{children}</div>
    </div>
  );
}

export function TiltCard({ children, width = 380 }: { children: ReactNode; width?: number }) {
  const card = useRef<HTMLDivElement>(null);

  function tilt(e: React.MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    if (card.current) card.current.style.transform = `rotateY(${x * 16}deg) rotateX(${-y * 16}deg)`;
  }

  function reset() {
    if (card.current) card.current.style.transform = "rotateY(0deg) rotateX(0deg)";
  }

  return (
    <div
      className="relative isolate"
      style={{ width, maxWidth: "100%", perspective: 1300, paddingRight: 22, paddingBottom: 24 }}
      onMouseMove={tilt}
      onMouseLeave={reset}
    >
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: "#e4d6fb", border: "1px solid #d8c4f5", borderRadius: 22, transform: "translate(20px,22px) rotate(4deg)" }}
      />
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: "#f4e9ff", border: "1px solid #e3d3fa", borderRadius: 22, transform: "translate(10px,11px) rotate(2deg)" }}
      />
      <div
        ref={card}
        className="relative z-10"
        style={{
          background: "rgba(255,255,255,0.92)",
          border: "1px solid rgba(255,255,255,0.9)",
          borderRadius: 22,
          padding: "40px 36px",
          transformStyle: "preserve-3d",
          boxShadow: "0 34px 70px rgba(150,110,210,0.28)",
          pointerEvents: "auto",
        }}
      >
        {children}
      </div>
    </div>
  );
}

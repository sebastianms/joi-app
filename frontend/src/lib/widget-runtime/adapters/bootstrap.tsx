// Bootstrap 5 adapter — uses Bootstrap class conventions via inline styles.

import type { CSSProperties, ReactNode } from "react";
import type { Adapter } from "./shadcn";

interface CardProps { children: ReactNode; style?: CSSProperties }
interface ButtonProps { children: ReactNode; onClick?: () => void; style?: CSSProperties }

export const BootstrapAdapter: Adapter = {
  name: "bootstrap" as const,

  Card({ children, style }: CardProps) {
    return (
      <div
        style={{
          borderRadius: "4px",
          border: "1px solid #dee2e6",
          background: "#fff",
          padding: "16px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
          ...style,
        }}
      >
        {children}
      </div>
    );
  },

  Button({ children, onClick, style }: ButtonProps) {
    return (
      <button
        onClick={onClick}
        style={{
          background: "#0d6efd",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          padding: "6px 14px",
          fontSize: "13px",
          fontWeight: 400,
          cursor: "pointer",
          ...style,
        }}
      >
        {children}
      </button>
    );
  },
};

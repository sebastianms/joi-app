// HeroUI adapter — modern look with soft shadows and violet accent.

import type { CSSProperties, ReactNode } from "react";
import type { Adapter } from "./shadcn";

interface CardProps { children: ReactNode; style?: CSSProperties }
interface ButtonProps { children: ReactNode; onClick?: () => void; style?: CSSProperties }

export const HeroUIAdapter: Adapter = {
  name: "heroui" as const,

  Card({ children, style }: CardProps) {
    return (
      <div
        style={{
          borderRadius: "12px",
          border: "1px solid rgba(139,92,246,0.2)",
          background: "rgba(139,92,246,0.05)",
          padding: "16px",
          boxShadow: "0 4px 24px rgba(139,92,246,0.1)",
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
          background: "linear-gradient(135deg, #7c3aed, #6d28d9)",
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          padding: "6px 14px",
          fontSize: "13px",
          fontWeight: 500,
          cursor: "pointer",
          boxShadow: "0 2px 8px rgba(109,40,217,0.3)",
          ...style,
        }}
      >
        {children}
      </button>
    );
  },
};

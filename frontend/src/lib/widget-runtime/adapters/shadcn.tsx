// Shadcn/ui adapter — minimal primitives used by widget renderers.
// Styled to match a dark, zinc-based theme.

import React, { type CSSProperties, type ReactNode } from "react";

interface CardProps { children: ReactNode; style?: CSSProperties }
interface ButtonProps { children: ReactNode; onClick?: () => void; style?: CSSProperties }

export const ShadcnAdapter = {
  name: "shadcn" as const,

  Card({ children, style }: CardProps) {
    return (
      <div
        style={{
          borderRadius: "8px",
          border: "1px solid rgba(255,255,255,0.1)",
          background: "#18181b",
          padding: "16px",
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
          background: "#18181b",
          color: "#e4e4e7",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: "6px",
          padding: "6px 14px",
          fontSize: "13px",
          fontWeight: 500,
          cursor: "pointer",
          ...style,
        }}
      >
        {children}
      </button>
    );
  },
};

export interface Adapter {
  name: string;
  Card(props: { children: ReactNode; style?: CSSProperties }): React.ReactElement;
  Button(props: { children: ReactNode; onClick?: () => void; style?: CSSProperties }): React.ReactElement;
}

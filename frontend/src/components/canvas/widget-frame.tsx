// Iframe shell for the widget canvas (FR-008, FR-008a).
//
// Responsibility: construir el documento srcdoc con CSP + sandbox y exponer
// el contentWindow al hook orquestador (use-canvas) para que pueda enviar
// widget:init y escuchar ready/error/resize. No gestiona ciclo de vida del
// widget: ese pertenece al hook (T133).
//
// CSP y flags de sandbox se definen en specs/004-widget-generation/research.md R4.

"use client";

import { forwardRef, useImperativeHandle, useMemo, useRef } from "react";

const CSP =
  "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'";

const SANDBOX_FLAGS = "allow-scripts";

interface WidgetFrameProps {
  bundleCode: string;
  title: string;
  onLoad?: () => void;
}

export interface WidgetFrameHandle {
  contentWindow: Window | null;
}

function buildSrcDoc(bundleCode: string): string {
  // Proteger contra </script> literal dentro del bundle rompiendo el tag contenedor.
  const safe = bundleCode.replace(/<\/script>/gi, "<\\/script>");
  return `<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="Content-Security-Policy" content="${CSP}" />
    <title>widget</title>
    <style>
      html, body { margin: 0; padding: 0; background: transparent; }
      body { font-family: system-ui, -apple-system, sans-serif; color: #111827; }
      #root { width: 100%; min-height: 100%; }
    </style>
  </head>
  <body>
    <div id="root" data-role="widget-root"></div>
    <script>${safe}</script>
  </body>
</html>`;
}

export const WidgetFrame = forwardRef<WidgetFrameHandle, WidgetFrameProps>(
  function WidgetFrame({ bundleCode, title, onLoad }, ref) {
    const iframeRef = useRef<HTMLIFrameElement | null>(null);
    const srcDoc = useMemo(() => buildSrcDoc(bundleCode), [bundleCode]);

    useImperativeHandle(
      ref,
      () => ({
        get contentWindow() {
          return iframeRef.current?.contentWindow ?? null;
        },
      }),
      [],
    );

    return (
      <iframe
        ref={iframeRef}
        title={title}
        aria-label={title}
        data-role="widget-frame"
        sandbox={SANDBOX_FLAGS}
        srcDoc={srcDoc}
        onLoad={onLoad}
        className="h-full w-full border-0 bg-transparent"
      />
    );
  },
);

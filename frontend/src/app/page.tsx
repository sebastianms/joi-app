import Link from "next/link";
import { ChatPanel } from "@/components/chat/chat-panel";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 font-sans dark:bg-black">
      <header className="flex items-center justify-between border-b border-border bg-background px-6 py-3">
        <h1 className="text-lg font-semibold tracking-tight">Joi-App</h1>
        <Link
          href="/setup"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          Configurar fuentes de datos
        </Link>
      </header>

      <main className="grid flex-1 grid-cols-1 gap-4 p-4 md:grid-cols-2">
        <div className="min-h-0">
          <ChatPanel />
        </div>
        <section
          className="flex min-h-0 items-center justify-center rounded-xl border border-dashed border-border bg-card text-center text-sm text-muted-foreground"
          aria-label="Canvas de widgets"
        >
          <p className="max-w-sm px-6">
            Los widgets generados aparecerán aquí cuando solicites visualizar tus datos.
          </p>
        </section>
      </main>
    </div>
  );
}

import { SQLConnectionForm } from "@/components/setup/sql-form";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 min-h-screen font-sans dark:bg-black">
      <main className="flex flex-1 w-full max-w-4xl flex-col items-center justify-center py-12 px-8 bg-zinc-50 dark:bg-black">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 mb-4">
            Joi-App Data Setup
          </h1>
          <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl">
            Configure your data sources to enable dynamic UI generation. Start by linking your relational database.
          </p>
        </div>
        
        <div className="w-full">
          <SQLConnectionForm />
        </div>
      </main>
    </div>
  );
}

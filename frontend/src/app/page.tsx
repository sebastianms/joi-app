"use client"

import { SQLConnectionForm } from "@/components/setup/sql-form";
import { JSONUploadForm } from "@/components/setup/json-form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 min-h-screen font-sans dark:bg-black">
      <main className="flex flex-1 w-full max-w-4xl flex-col items-center py-12 px-8 bg-zinc-50 dark:bg-black">
        <div className="text-center mb-10 mt-8">
          <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 mb-4">
            Joi-App Data Setup
          </h1>
          <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
            Configure your data sources to enable dynamic UI generation. Link your relational database or upload a static JSON file.
          </p>
        </div>
        
        <div className="w-full max-w-2xl mx-auto">
          <Tabs defaultValue="sql" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-8">
              <TabsTrigger value="sql">SQL Database</TabsTrigger>
              <TabsTrigger value="json">JSON File</TabsTrigger>
            </TabsList>
            <TabsContent value="sql" className="mt-0">
              <div className="bg-white dark:bg-zinc-950 p-6 rounded-xl border shadow-sm">
                <SQLConnectionForm />
              </div>
            </TabsContent>
            <TabsContent value="json" className="mt-0">
              <div className="bg-white dark:bg-zinc-950 p-6 rounded-xl border shadow-sm">
                <JSONUploadForm />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}

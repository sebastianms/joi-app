"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";

// Esquema Zod basado en Pydantic
const connectionSchema = z.object({
  name: z.string().min(2, "Connection name must be at least 2 characters"),
  source_type: z.enum(["POSTGRESQL", "MYSQL", "SQLITE", "FILE"]),
  connection_string: z.string().min(5, "Must be a valid database connection string (e.g. sqlite+aiosqlite:///...)"),
  user_session_id: z.string(), // Oculto o auto-generado
});

type ConnectionFormValues = z.infer<typeof connectionSchema>;

export function SQLConnectionForm() {
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const form = useForm<ConnectionFormValues>({
    resolver: zodResolver(connectionSchema),
    defaultValues: {
      name: "",
      source_type: "POSTGRESQL",
      connection_string: "",
      user_session_id: "demo-session-123", // Harcodeado temporalmente
    },
  });

  async function onSubmit(data: ConnectionFormValues) {
    setTestResult(null);
    setErrorMessage(null);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
      const response = await fetch(`${baseUrl}/connections/sql`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Unknown error connecting to DB");
      }

      const result = await response.json();
      setTestResult("success");
      console.log("Connection saved:", result);
    } catch (error) {
      setTestResult("error");
      setErrorMessage(error instanceof Error ? error.message : "An unexpected error occurred");
    }
  }

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-card rounded-lg shadow-sm border border-border">
      <h2 className="text-2xl font-bold mb-6 text-foreground">Connect Database</h2>

      {testResult === "success" && (
        <Alert className="mb-6 border-green-500 text-green-700 bg-green-50 dark:bg-green-950/50">
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>
            Connection established and saved successfully.
          </AlertDescription>
        </Alert>
      )}

      {testResult === "error" && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Connection Failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      <form 
        onSubmit={(e) => {
          e.preventDefault();
          const formData = new FormData(e.currentTarget);
          const data = {
            name: formData.get("name") as string,
            source_type: formData.get("source_type") as ConnectionFormValues["source_type"],
            connection_string: formData.get("connection_string") as string,
            user_session_id: "demo-session-123"
          };
          onSubmit(data);
        }} 
        className="space-y-6"
      >
        <div className="space-y-2">
          <label className="text-sm font-medium">Connection Name</label>
          <input 
            name="name" 
            placeholder="Production DB" 
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Engine</label>
          <select
            name="source_type"
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            required
          >
            <option value="POSTGRESQL">PostgreSQL</option>
            <option value="MYSQL">MySQL</option>
            <option value="SQLITE">SQLite</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Connection String</label>
          <input
            name="connection_string"
            placeholder="postgresql+asyncpg://user:pass@host/db"
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            required
          />
        </div>

        <Button type="submit" className="w-full">
          Connect
        </Button>
      </form>
    </div>
  );
}

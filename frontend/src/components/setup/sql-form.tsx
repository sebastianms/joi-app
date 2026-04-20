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
  connection_string: z.string().url("Must be a valid database connection string (e.g. postgresql://...)"),
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
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
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
    } catch (error: any) {
      setTestResult("error");
      setErrorMessage(error.message);
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

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Connection Name</FormLabel>
                <FormControl>
                  <Input placeholder="Production DB" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="source_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Engine</FormLabel>
                <FormControl>
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    {...field}
                  >
                    <option value="POSTGRESQL">PostgreSQL</option>
                    <option value="MYSQL">MySQL</option>
                    <option value="SQLITE">SQLite</option>
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="connection_string"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Connection String</FormLabel>
                <FormControl>
                  <Input
                    placeholder="postgresql+asyncpg://user:pass@host/db"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Standard SQLAlchemy connection string.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Testing connection..." : "Connect"}
          </Button>
        </form>
      </Form>
    </div>
  );
}

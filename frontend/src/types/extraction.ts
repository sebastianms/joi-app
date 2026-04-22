/**
 * Tipos TypeScript para el contrato `data_extraction.v1`.
 *
 * Mantener alineado 1:1 con `specs/003-data-agent/contracts/data-extraction-v1.schema.json`.
 * Consumido por el chat (Feature 003) y el Widget Generation (Feature 004).
 */

export type SourceType =
  | "SQL_POSTGRESQL"
  | "SQL_MYSQL"
  | "SQL_SQLITE"
  | "JSON";

export type QueryLanguage = "sql" | "jsonpath";

export type ColumnType =
  | "string"
  | "integer"
  | "float"
  | "boolean"
  | "datetime"
  | "null"
  | "unknown";

export type ExtractionStatus = "success" | "error";

export type ErrorCode =
  | "NO_CONNECTION"
  | "SECURITY_REJECTION"
  | "QUERY_SYNTAX"
  | "TARGET_NOT_FOUND"
  | "PERMISSION_DENIED"
  | "TIMEOUT"
  | "AMBIGUOUS_PROMPT"
  | "SOURCE_UNAVAILABLE"
  | "UNKNOWN";

export interface QueryPlan {
  language: QueryLanguage;
  expression: string;
  parameters?: Record<string, unknown>;
  generated_by_model?: string;
}

export interface ColumnDescriptor {
  name: string;
  type: ColumnType;
}

export interface ExtractionError {
  code: ErrorCode;
  message: string;
  technical_detail?: string;
}

export type ExtractionRow = Record<string, unknown>;

export interface DataExtraction {
  contract_version: "v1";
  extraction_id: string;
  session_id: string;
  connection_id: string;
  source_type: SourceType;
  query_plan: QueryPlan;
  columns: ColumnDescriptor[];
  rows: ExtractionRow[];
  row_count: number;
  truncated: boolean;
  status: ExtractionStatus;
  error?: ExtractionError | null;
  generated_at: string;
}

export type TracePipeline = "sql" | "json";

export interface AgentTrace {
  trace_id: string;
  extraction_id: string;
  pipeline: TracePipeline;
  query_display: string;
  preview_rows: ExtractionRow[];
  preview_columns: ColumnDescriptor[];
  security_rejection: boolean;
  collapsed: boolean;
  created_at: string;
}

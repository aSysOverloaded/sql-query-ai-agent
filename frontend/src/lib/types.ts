export type QueryResult = {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
};

export type QueryCost = {
  level: "low" | "medium" | "high";
  rows_scanned: number;
  notes: string[];
  plan: string[];
};

export type ChatResponse = {
  thread_id: string;
  intent: string | null;
  reply: string;
  sql: string | null;
  explanation: string | null;
  warnings: string[];
  result: QueryResult | null;
  cost?: QueryCost | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
  error?: string;
  retryText?: string;
};

export type Conversation = {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMessage[];
};

export type ForeignKey = {
  column: string;
  references_table: string;
  references_column: string;
};

export type SchemaTable = {
  columns: Record<string, string>;
  foreign_keys: ForeignKey[];
};

export type Schema = Record<string, SchemaTable>;

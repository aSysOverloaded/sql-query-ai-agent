import type { ChatMessage, Conversation } from "@/lib/types";

const STORAGE_KEY = "sql-agent-conversations";
const MAX_SAVED_ROWS = 50;

export function loadConversations(): Conversation[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function withFewerRows(message: ChatMessage): ChatMessage {
  const result = message.response?.result;
  if (!message.response || !result || result.rows.length <= MAX_SAVED_ROWS) return message;
  const rows = result.rows.slice(0, MAX_SAVED_ROWS);
  return {
    ...message,
    response: { ...message.response, result: { ...result, rows, row_count: rows.length, truncated: true } },
  };
}

export function saveConversations(conversations: Conversation[]): void {
  const compact = conversations.map((conversation) => ({
    ...conversation,
    messages: conversation.messages.map(withFewerRows),
  }));
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(compact));
  } catch {}
}

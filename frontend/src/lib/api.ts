import type { ChatResponse, Schema } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const OFFLINE_MESSAGE = "Can't reach the server. Is the backend running on port 8000?";

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {}
  return `Request failed with status ${response.status}.`;
}

function parseEvent(raw: string) {
  let event = "message";
  let data = "";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7);
    else if (line.startsWith("data: ")) data += line.slice(6);
  }
  return { event, data: data ? JSON.parse(data) : {} };
}

export async function fetchSchema(): Promise<Schema> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/schema`);
  } catch {
    throw new Error(OFFLINE_MESSAGE);
  }
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function streamChat(
  message: string,
  threadId: string,
  onProgress: (label: string) => void,
): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, thread_id: threadId }),
    });
  } catch {
    throw new Error(OFFLINE_MESSAGE);
  }
  if (!response.ok || !response.body) throw new Error(await readError(response));

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const raw of events) {
      const { event, data } = parseEvent(raw);
      if (event === "progress") onProgress(data.label);
      if (event === "result") return data as ChatResponse;
      if (event === "error") throw new Error(data.detail);
    }
  }
  throw new Error("The connection closed before an answer arrived. Please try again.");
}

"use client";

import { useEffect, useRef, useState } from "react";

import { AssistantMessage } from "@/components/AssistantMessage";
import { ChatInput } from "@/components/ChatInput";
import { EmptyState } from "@/components/EmptyState";
import { MenuIcon } from "@/components/icons";
import { ProgressSteps } from "@/components/ProgressSteps";
import { Sidebar } from "@/components/Sidebar";
import { UserMessage } from "@/components/UserMessage";
import { streamChat } from "@/lib/api";
import { loadConversations, saveConversations } from "@/lib/storage";
import type { ChatMessage, Conversation } from "@/lib/types";

function newConversation(): Conversation {
  return { id: crypto.randomUUID(), title: "New chat", createdAt: Date.now(), messages: [] };
}

function initialConversations(): Conversation[] {
  const saved = loadConversations();
  return saved.length ? saved : [newConversation()];
}

export function ChatApp() {
  const [conversations, setConversations] = useState<Conversation[]>(initialConversations);
  const [activeId, setActiveId] = useState<string | null>(() => conversations[0]?.id ?? null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const active = conversations.find((conversation) => conversation.id === activeId);

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [active?.messages.length, progress.length]);

  function updateConversation(id: string, update: (conversation: Conversation) => Conversation) {
    setConversations((current) => current.map((conversation) => (conversation.id === id ? update(conversation) : conversation)));
  }

  function appendMessage(id: string, message: ChatMessage) {
    updateConversation(id, (conversation) => ({
      ...conversation,
      title: conversation.messages.length ? conversation.title : message.content.slice(0, 48),
      messages: [...conversation.messages, message],
    }));
  }

  async function send(text: string) {
    if (!active || loading) return;
    const conversationId = active.id;
    appendMessage(conversationId, { id: crypto.randomUUID(), role: "user", content: text });
    setLoading(true);
    setProgress([]);
    try {
      const response = await streamChat(text, conversationId, (label) => setProgress((steps) => [...steps, label]));
      appendMessage(conversationId, { id: crypto.randomUUID(), role: "assistant", content: response.reply, response });
    } catch (error) {
      appendMessage(conversationId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        error: error instanceof Error ? error.message : "Something went wrong. Please try again.",
        retryText: text,
      });
    } finally {
      setLoading(false);
      setProgress([]);
    }
  }

  function retry(message: ChatMessage) {
    if (!active || !message.retryText) return;
    updateConversation(active.id, (conversation) => ({ ...conversation, messages: conversation.messages.slice(0, -2) }));
    send(message.retryText);
  }

  function startNewChat() {
    setSidebarOpen(false);
    if (active && active.messages.length === 0) return;
    const conversation = newConversation();
    setConversations((current) => [conversation, ...current]);
    setActiveId(conversation.id);
  }

  function selectConversation(id: string) {
    setActiveId(id);
    setSidebarOpen(false);
  }

  function deleteConversation(id: string) {
    const remaining = conversations.filter((conversation) => conversation.id !== id);
    const next = remaining.length ? remaining : [newConversation()];
    setConversations(next);
    if (id === activeId) setActiveId(next[0].id);
  }

  const messages = active?.messages ?? [];
  const lastMessage = messages[messages.length - 1];

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={startNewChat}
        onSelect={selectConversation}
        onDelete={deleteConversation}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 lg:hidden"
            aria-label="Open sidebar"
          >
            <MenuIcon className="size-5" />
          </button>
          <h2 className="truncate text-sm font-medium">{active?.title ?? "New chat"}</h2>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl space-y-6 px-4 py-6">
            {messages.length === 0 && !loading && <EmptyState onPick={send} />}
            {messages.map((message) =>
              message.role === "user" ? (
                <UserMessage key={message.id} text={message.content} />
              ) : (
                <AssistantMessage
                  key={message.id}
                  message={message}
                  onRetry={message === lastMessage && !loading ? () => retry(message) : undefined}
                />
              ),
            )}
            {loading && <ProgressSteps steps={progress} />}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="border-t border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
          <div className="mx-auto max-w-4xl px-4 py-3">
            <ChatInput onSend={send} disabled={loading} />
            <p className="mt-2 text-center text-xs text-zinc-400">
              Read-only: the assistant never modifies data. Enter to send, Shift+Enter for a new line.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

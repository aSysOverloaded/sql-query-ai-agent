"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { SendIcon } from "@/components/icons";

const MAX_LENGTH = 2000;

type ChatInputProps = {
  onSend: (text: string) => void;
  disabled: boolean;
};

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = !disabled && text.trim().length > 0 && text.length <= MAX_LENGTH;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, [text]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!canSend) return;
    onSend(text.trim());
    setText("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      onSubmit={submit}
      className="flex items-end gap-2 rounded-2xl border border-zinc-200 bg-white p-2 shadow-sm focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-500/10 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        placeholder="Ask a question, or paste SQL to explain, debug or optimize…"
        className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:truncate placeholder:text-zinc-400"
        aria-label="Message"
      />
      <div className="flex items-center gap-2">
        {text.length > MAX_LENGTH * 0.8 && (
          <span className={`text-xs tabular-nums ${text.length > MAX_LENGTH ? "text-rose-500" : "text-zinc-400"}`}>
            {text.length}/{MAX_LENGTH}
          </span>
        )}
        <button
          type="submit"
          disabled={!canSend}
          className="flex size-9 items-center justify-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:disabled:bg-zinc-700"
          aria-label="Send message"
        >
          <SendIcon className="size-4" />
        </button>
      </div>
    </form>
  );
}

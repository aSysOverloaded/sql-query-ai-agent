import { CloseIcon, DatabaseIcon, PlusIcon, TrashIcon } from "@/components/icons";
import { SchemaBrowser } from "@/components/SchemaBrowser";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { Conversation } from "@/lib/types";

type SidebarProps = {
  conversations: Conversation[];
  activeId: string | null;
  open: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
};

export function Sidebar({ conversations, activeId, open, onClose, onNewChat, onSelect, onDelete }: SidebarProps) {
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} aria-hidden="true" />}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-zinc-200 bg-zinc-50 transition-transform dark:border-zinc-800 dark:bg-zinc-950 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <DatabaseIcon className="size-4" />
            </div>
            <span className="text-sm font-semibold">SQL Assistant</span>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800 lg:hidden" aria-label="Close sidebar">
            <CloseIcon className="size-5" />
          </button>
        </div>

        <div className="px-3">
          <button
            onClick={onNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm font-medium shadow-sm transition hover:border-indigo-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-indigo-500/40"
          >
            <PlusIcon className="size-4" />
            New chat
          </button>
        </div>

        <nav className="mt-4 min-h-0 flex-1 overflow-y-auto px-3">
          <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-zinc-400">History</p>
          <ul className="space-y-0.5">
            {conversations.map((conversation) => (
              <li key={conversation.id} className="group relative">
                <button
                  onClick={() => onSelect(conversation.id)}
                  className={`w-full truncate rounded-lg py-2 pl-3 pr-8 text-left text-sm transition ${
                    conversation.id === activeId
                      ? "bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300"
                      : "text-zinc-600 hover:bg-zinc-200/60 dark:text-zinc-400 dark:hover:bg-zinc-800"
                  }`}
                >
                  {conversation.title}
                </button>
                <button
                  onClick={() => onDelete(conversation.id)}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-1 text-zinc-400 transition hover:bg-rose-50 hover:text-rose-500 dark:text-zinc-500 dark:hover:bg-rose-500/10"
                  aria-label={`Delete ${conversation.title}`}
                  title="Delete chat"
                >
                  <TrashIcon className="size-4" />
                </button>
              </li>
            ))}
          </ul>

          <p className="mt-6 px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-zinc-400">Database schema</p>
          <SchemaBrowser />
        </nav>

        <div className="border-t border-zinc-200 p-3 dark:border-zinc-800">
          <ThemeToggle />
        </div>
      </aside>
    </>
  );
}

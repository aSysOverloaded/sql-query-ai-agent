import { SparkIcon, WarningIcon } from "@/components/icons";
import { Markdown } from "@/components/Markdown";
import { ResultsTable } from "@/components/ResultsTable";
import { SqlCode } from "@/components/SqlCode";
import type { ChatMessage } from "@/lib/types";

const INTENT_LABELS: Record<string, { label: string; className: string }> = {
  generate_sql: { label: "SQL query", className: "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300" },
  explain_sql: { label: "Explanation", className: "bg-sky-50 text-sky-700 dark:bg-sky-500/10 dark:text-sky-300" },
  optimize_sql: { label: "Optimization", className: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300" },
  debug_sql: { label: "Debugging", className: "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300" },
  schema_info: { label: "Schema", className: "bg-violet-50 text-violet-700 dark:bg-violet-500/10 dark:text-violet-300" },
  destructive: { label: "Blocked", className: "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300" },
  out_of_scope: { label: "Out of scope", className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300" },
};

function Avatar() {
  return (
    <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white">
      <SparkIcon className="size-4" />
    </div>
  );
}

function Warnings({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <div className="flex gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
      <WarningIcon className="mt-0.5 size-4 shrink-0" />
      <div className="space-y-1">
        {warnings.map((warning) => (
          <p key={warning}>{warning}</p>
        ))}
      </div>
    </div>
  );
}

type AssistantMessageProps = {
  message: ChatMessage;
  onRetry?: () => void;
};

export function AssistantMessage({ message, onRetry }: AssistantMessageProps) {
  if (message.error) {
    return (
      <div className="flex gap-3">
        <Avatar />
        <div className="flex-1 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
          <p>{message.error}</p>
          {onRetry && (
            <button onClick={onRetry} className="mt-2 font-medium underline underline-offset-2 hover:no-underline">
              Try again
            </button>
          )}
        </div>
      </div>
    );
  }

  const response = message.response;
  const intent = response?.intent ? INTENT_LABELS[response.intent] : undefined;
  const isQueryAnswer = Boolean(response?.sql && response.result);

  return (
    <div className="flex gap-3">
      <Avatar />
      <div className="min-w-0 flex-1 space-y-3">
        {intent && (
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${intent.className}`}>
            {intent.label}
          </span>
        )}
        {response && isQueryAnswer ? (
          <>
            <SqlCode code={response.sql!} title="Generated SQL" downloadable />
            <Warnings warnings={response.warnings} />
            {response.explanation && (
              <div className="rounded-xl border border-zinc-200 px-4 py-3 dark:border-zinc-800">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Explanation</p>
                <Markdown text={response.explanation} />
              </div>
            )}
            <ResultsTable result={response.result!} cost={response.cost} />
          </>
        ) : (
          <>
            <Markdown text={message.content} />
            {response && <Warnings warnings={response.warnings} />}
          </>
        )}
      </div>
    </div>
  );
}

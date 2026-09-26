import type { QueryCost } from "@/lib/types";

const LEVEL_STYLES: Record<QueryCost["level"], string> = {
  low: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300",
  medium: "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300",
  high: "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300",
};

export function CostBadge({ cost }: { cost: QueryCost }) {
  return (
    <details className="group border-b border-zinc-200 px-4 py-2 text-xs dark:border-zinc-800">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-zinc-500">
        <span className={`rounded-full px-2 py-0.5 font-medium capitalize ${LEVEL_STYLES[cost.level]}`}>
          {cost.level} cost
        </span>
        <span>Estimated {cost.rows_scanned.toLocaleString()} rows read</span>
        <span className="ml-auto underline-offset-2 group-open:hidden hover:underline">Show query plan</span>
        <span className="ml-auto hidden underline-offset-2 group-open:inline hover:underline">Hide query plan</span>
      </summary>
      <ul className="mt-2 list-disc space-y-0.5 pl-5 text-zinc-600 dark:text-zinc-400">
        {cost.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </details>
  );
}

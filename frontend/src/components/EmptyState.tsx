import { DatabaseIcon } from "@/components/icons";

const EXAMPLES = [
  {
    group: "Ask for data",
    prompts: [
      "Show all employees hired after January 2024",
      "Total revenue by product category, highest first",
      "Which products have never been ordered?",
    ],
  },
  {
    group: "Work with SQL",
    prompts: [
      "Why does this fail? SELECT nme FROM products",
      "Make this faster: SELECT * FROM orders WHERE strftime('%Y', order_date) = '2024'",
      "What is the difference between WHERE and HAVING?",
    ],
  },
  {
    group: "Explore the database",
    prompts: ["What tables do you have?", "How are customers connected to products?"],
  },
];

export function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center pt-8 text-center sm:pt-16">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/20">
        <DatabaseIcon className="size-6" />
      </div>
      <h1 className="mt-5 text-2xl font-semibold tracking-tight">Ask your database anything</h1>
      <p className="mt-2 max-w-lg text-sm text-zinc-500">
        Questions become validated, read-only SQL for a retail company database, with the results and a
        plain-English explanation. Follow-up questions refine the previous query.
      </p>
      <div className="mt-10 grid w-full gap-6 text-left sm:grid-cols-3">
        {EXAMPLES.map(({ group, prompts }) => (
          <div key={group}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">{group}</p>
            <div className="space-y-2">
              {prompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => onPick(prompt)}
                  className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2.5 text-left text-sm text-zinc-700 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-indigo-500/40 dark:hover:bg-indigo-500/5"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

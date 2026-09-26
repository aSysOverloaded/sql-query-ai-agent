import { CheckIcon, SparkIcon } from "@/components/icons";

export function ProgressSteps({ steps }: { steps: string[] }) {
  const visibleSteps = steps.length ? steps : ["Sending your question…"];

  return (
    <div className="flex gap-3" role="status" aria-live="polite">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white">
        <SparkIcon className="size-4 animate-spin [animation-duration:3s]" />
      </div>
      <ol className="space-y-1.5 pt-1 text-sm">
        {visibleSteps.map((step, index) => {
          const isCurrent = index === visibleSteps.length - 1;
          return (
            <li key={index} className={`flex items-center gap-2 ${isCurrent ? "text-zinc-900 dark:text-zinc-100" : "text-zinc-400"}`}>
              {isCurrent ? (
                <span className="size-3.5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
              ) : (
                <CheckIcon className="size-3.5 text-emerald-500" />
              )}
              {step}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

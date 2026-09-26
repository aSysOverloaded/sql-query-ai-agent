import { DownloadIcon } from "@/components/icons";
import { downloadFile, toCsv } from "@/lib/download";
import type { QueryResult } from "@/lib/types";

function Cell({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="italic text-zinc-400">NULL</span>;
  }
  return <>{String(value)}</>;
}

export function ResultsTable({ result }: { result: QueryResult }) {
  const summary = result.truncated
    ? `Showing the first ${result.row_count} rows`
    : `${result.row_count} ${result.row_count === 1 ? "row" : "rows"}`;

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Results · <span className="normal-case">{summary}</span>
        </span>
        <button
          onClick={() => downloadFile("results.csv", toCsv(result), "text/csv")}
          className="toolbar-button"
          aria-label="Download results as CSV"
        >
          <DownloadIcon className="size-4" />
          <span>CSV</span>
        </button>
      </div>
      {result.row_count === 0 ? (
        <p className="px-4 py-6 text-center text-sm text-zinc-500">The query returned no rows.</p>
      ) : (
        <div className="max-h-80 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-zinc-100 dark:bg-zinc-900">
              <tr>
                {result.columns.map((column) => (
                  <th key={column} className="whitespace-nowrap px-4 py-2 font-medium text-zinc-600 dark:text-zinc-300">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {result.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50">
                  {row.map((value, columnIndex) => (
                    <td
                      key={columnIndex}
                      className={`whitespace-nowrap px-4 py-2 ${typeof value === "number" ? "text-right tabular-nums" : ""}`}
                    >
                      <Cell value={value} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

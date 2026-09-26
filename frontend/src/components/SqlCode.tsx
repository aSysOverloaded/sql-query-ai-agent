"use client";

import hljs from "highlight.js/lib/core";
import sql from "highlight.js/lib/languages/sql";
import { useMemo, useState } from "react";

import { CheckIcon, CopyIcon, DownloadIcon } from "@/components/icons";
import { downloadFile } from "@/lib/download";

hljs.registerLanguage("sql", sql);

type SqlCodeProps = {
  code: string;
  title?: string;
  downloadable?: boolean;
};

export function SqlCode({ code, title = "SQL", downloadable = false }: SqlCodeProps) {
  const [copied, setCopied] = useState(false);
  const highlighted = useMemo(() => hljs.highlight(code, { language: "sql" }).value, [code]);

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900/60">
      <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</span>
        <div className="flex items-center gap-1">
          <button onClick={copy} className="toolbar-button" aria-label="Copy SQL">
            {copied ? <CheckIcon className="size-4 text-emerald-500" /> : <CopyIcon className="size-4" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>
          {downloadable && (
            <button
              onClick={() => downloadFile("query.sql", code, "application/sql")}
              className="toolbar-button"
              aria-label="Download SQL"
            >
              <DownloadIcon className="size-4" />
              <span>.sql</span>
            </button>
          )}
        </div>
      </div>
      <pre className="overflow-x-auto p-4 text-[13px] leading-relaxed">
        <code className="hljs font-mono" dangerouslySetInnerHTML={{ __html: highlighted }} />
      </pre>
    </div>
  );
}

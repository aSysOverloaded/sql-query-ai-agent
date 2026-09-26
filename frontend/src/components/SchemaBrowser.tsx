"use client";

import { useEffect, useState } from "react";

import { ChevronIcon } from "@/components/icons";
import { fetchSchema } from "@/lib/api";
import type { Schema } from "@/lib/types";

export function SchemaBrowser() {
  const [schema, setSchema] = useState<Schema | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openTable, setOpenTable] = useState<string | null>(null);

  useEffect(() => {
    fetchSchema()
      .then(setSchema)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  if (error) return <p className="px-2 text-xs text-rose-500">{error}</p>;
  if (!schema) return <p className="px-2 text-xs text-zinc-400">Loading schema…</p>;

  return (
    <ul className="space-y-0.5">
      {Object.entries(schema).map(([table, details]) => {
        const isOpen = openTable === table;
        const foreignKeys = new Map(details.foreign_keys.map((key) => [key.column, key]));
        return (
          <li key={table}>
            <button
              onClick={() => setOpenTable(isOpen ? null : table)}
              className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-sm text-zinc-600 hover:bg-zinc-200/60 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              <ChevronIcon className={`size-3.5 transition-transform ${isOpen ? "rotate-90" : ""}`} />
              <span className="font-mono">{table}</span>
            </button>
            {isOpen && (
              <ul className="mb-1 ml-6 space-y-0.5 border-l border-zinc-200 pl-3 dark:border-zinc-800">
                {Object.entries(details.columns).map(([column, type]) => {
                  const foreignKey = foreignKeys.get(column);
                  return (
                    <li key={column} className="text-xs leading-5">
                      <span className="font-mono text-zinc-700 dark:text-zinc-300">{column}</span>{" "}
                      <span className="text-zinc-400">{type.toLowerCase()}</span>
                      {foreignKey && (
                        <span className="block text-indigo-500">
                          → {foreignKey.references_table}.{foreignKey.references_column}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}

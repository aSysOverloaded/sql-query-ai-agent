import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { SqlCode } from "@/components/SqlCode";

const components: Components = {
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children }) => {
    const text = String(children).replace(/\n$/, "");
    const isBlock = Boolean(className) || text.includes("\n");
    if (isBlock) return <SqlCode code={text} />;
    return <code className="inline-code">{children}</code>;
  },
};

export function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}

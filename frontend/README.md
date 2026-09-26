# Frontend — SQL Assistant UI

Next.js 16 (App Router) + TypeScript + Tailwind CSS. See the [main README](../README.md) for the full project.

```bash
npm install
npm run dev      # http://localhost:3000 (expects the backend on http://localhost:8000)
```

| Path | Purpose |
|---|---|
| `src/components/ChatApp.tsx` | All chat state: conversations, sending, retry, history |
| `src/components/AssistantMessage.tsx` | Renders an answer: SQL panel, explanation, results, or formatted text |
| `src/lib/api.ts` | API client; `streamChat` reads Server-Sent Events from `/api/chat/stream` |
| `src/lib/storage.ts` | Conversation history in `localStorage` |

Set `NEXT_PUBLIC_API_URL` to point at a different backend.

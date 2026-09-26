"use client";

import dynamic from "next/dynamic";

const ChatApp = dynamic(() => import("@/components/ChatApp").then((module) => module.ChatApp), {
  ssr: false,
});

export default function Home() {
  return <ChatApp />;
}

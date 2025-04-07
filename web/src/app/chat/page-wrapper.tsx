"use client";

import { Suspense } from "react";
import ChatPageClient from "./page-client";

export default function ChatPageWrapper() {
  return (
    <Suspense fallback={<div className="p-4">Loading chat...</div>}>
      <ChatPageClient />
    </Suspense>
  );
}

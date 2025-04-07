"use client";

import { Suspense } from "react";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense fallback={<div className="p-4">Loading chat...</div>}>
      {children}
    </Suspense>
  );
}

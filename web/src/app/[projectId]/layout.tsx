"use client";

import * as React from "react";

export default function ProjectLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}>) {
  React.use(params);

  return (
    <>
      <main className="flex-1 p-6 min-w-0">{children}</main>
    </>
  );
}

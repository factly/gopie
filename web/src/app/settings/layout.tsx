"use client";

import * as React from "react";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 pb-8 space-y-8">
      <div className="space-y-0.5">
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">
          Manage your account settings and preferences.
        </p>
      </div>
      <div className="space-y-6">{children}</div>
    </div>
  );
}

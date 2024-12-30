"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import Editor from "@monaco-editor/react";

interface SqlPreviewProps {
  value: string;
  language?: string;
  height?: string;
}

export function SqlPreview({
  value,
  language = "sql",
  height = "150px",
}: SqlPreviewProps) {
  const { theme } = useTheme();

  return (
    <div className="overflow-hidden rounded-[var(--radius)] [&_.monaco-editor]:rounded-[var(--radius)]">
      <Editor
        height={height}
        defaultLanguage={language}
        value={value}
        theme={theme === "dark" ? "vs-dark" : "vs-light"}
        options={{
          readOnly: true,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: "off",
          roundedSelection: false,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          folding: false,
          wordWrap: "on",
        }}
        className="rounded-[var(--radius)]"
      />
    </div>
  );
}

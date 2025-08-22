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
  const { resolvedTheme: theme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="h-full w-full">
      <Editor
        height={height}
        defaultLanguage={language}
        value={value}
        theme={mounted && theme === "dark" ? "vs-dark" : "vs-light"}
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
        className="h-full w-full"
      />
    </div>
  );
}

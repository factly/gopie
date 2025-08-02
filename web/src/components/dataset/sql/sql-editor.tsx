"use client";

import * as React from "react";
import * as monaco from "monaco-editor";
import { useTheme } from "next-themes";
import Editor, { BeforeMount, OnMount } from "@monaco-editor/react";

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  schema?: Array<{ column_name: string; column_type: string }>;
  datasetId: string;
}

export function SqlEditor({
  value,
  onChange,
  schema,
  datasetId,
}: SqlEditorProps) {
  const { theme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  const editorRef = React.useRef<monaco.editor.IStandaloneCodeEditor | null>(
    null,
  );

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const handleEditorDidMount: OnMount = (editor) => {
    editorRef.current = editor;
  };

  const beforeMount: BeforeMount = (monaco) => {
    monaco.languages.registerCompletionItemProvider("sql", {
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const suggestions = [
          ...[
            "SELECT",
            "FROM",
            "WHERE",
            "GROUP BY",
            "ORDER BY",
            "LIMIT",
            "DESC",
            "ASC",
            "AND",
            "OR",
            "NOT",
            "NULL",
            "IS",
            "IN",
          ].map((keyword) => ({
            label: keyword,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: keyword,
            range: range,
          })),
          {
            label: "dataset",
            kind: monaco.languages.CompletionItemKind.Class,
            insertText: datasetId,
            detail: "Main dataset table",
            range: range,
          },
        ];

        if (schema) {
          suggestions.push(
            ...schema.map((col) => ({
              label: col.column_name,
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: col.column_name,
              detail: `Column (${col.column_type})`,
              range: range,
            })),
          );
        }

        return { suggestions };
      },
    });
  };

  return (
    <Editor
      height="200px"
      defaultLanguage="sql"
      value={value}
      onChange={(value) => onChange(value || "")}
      theme={mounted && theme === "dark" ? "vs-dark" : "vs-light"}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: "off",
        roundedSelection: false,
        scrollBeyondLastLine: false,
        automaticLayout: true,
        suggest: {
          showWords: false,
        },
      }}
      beforeMount={beforeMount}
      onMount={handleEditorDidMount}
    />
  );
}

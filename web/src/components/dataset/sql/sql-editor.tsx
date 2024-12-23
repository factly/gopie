"use client";

import * as React from "react";
import * as monaco from "monaco-editor";
import { useTheme } from "next-themes";
import Editor, { BeforeMount, OnMount } from "@monaco-editor/react";
import { Toggle } from "@/components/ui/toggle";
import { KeyboardIcon } from "lucide-react";

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
  const editorRef = React.useRef<monaco.editor.IStandaloneCodeEditor | null>(
    null
  );
  const [isVimMode, setIsVimMode] = React.useState(false);
  const statusBarRef = React.useRef<HTMLDivElement>(null);
  type VimMode = { dispose: () => void };
  const vimModeRef = React.useRef<VimMode | null>(null);

  const handleEditorDidMount: OnMount = (editor) => {
    editorRef.current = editor;

    if (isVimMode) {
      initVimMode(editor);
    }
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
            }))
          );
        }

        return { suggestions };
      },
    });
  };

  const initVimMode = React.useCallback(
    (editor: monaco.editor.IStandaloneCodeEditor) => {
      window.require.config({
        paths: {
          "monaco-vim": "https://unpkg.com/monaco-vim/dist/monaco-vim",
        },
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      window.require(["monaco-vim"], function (MonacoVim: any) {
        if (vimModeRef.current) {
          vimModeRef.current.dispose();
        }
        vimModeRef.current = MonacoVim.initVimMode(
          editor,
          statusBarRef.current
        );
      });
    },
    []
  );

  React.useEffect(() => {
    const editor = editorRef.current;
    if (editor) {
      if (isVimMode) {
        initVimMode(editor);
      } else if (vimModeRef.current) {
        vimModeRef.current.dispose();
      }
    }
  }, [isVimMode, initVimMode]);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Toggle
          aria-label="Toggle Vim mode"
          pressed={isVimMode}
          onPressedChange={setIsVimMode}
          size="sm"
        >
          <KeyboardIcon className="h-4 w-4 mr-1" />
          Vim Mode
        </Toggle>
        {isVimMode && (
          <code
            ref={statusBarRef}
            className="text-sm font-mono text-muted-foreground bg-muted/30 px-2 py-1 rounded"
          />
        )}
      </div>
      <Editor
        height="200px"
        defaultLanguage="sql"
        value={value}
        onChange={(value) => onChange(value || "")}
        theme={theme === "dark" ? "vs-dark" : "vs-light"}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: "on",
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
    </div>
  );
}

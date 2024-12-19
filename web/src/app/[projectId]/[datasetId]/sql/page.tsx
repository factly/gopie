"use client";

import * as React from "react";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { Button } from "@/components/ui/button";
import { PlayIcon } from "lucide-react";
import { toast } from "sonner";
import { ResultsTable } from "@/components/dataset/sql/results-table";
import { useTheme } from "next-themes";
import Editor, { BeforeMount } from "@monaco-editor/react";
import { useGetSchema } from "@/lib/queries/dataset/get-schema";

export default function SqlPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const { projectId, datasetId } = React.use(params);
  const [query, setQuery] = React.useState(
    `SELECT * FROM ${datasetId} LIMIT 10`
  );
  const [results, setResults] = React.useState<any>(null);
  const { theme } = useTheme();
  const executeSql = useDatasetSql();
  const editorRef = React.useRef<any>(null);

  const { data: schema } = useGetSchema({
    variables: {
      datasetId,
    },
  });

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor;
  };

  const beforeMount: BeforeMount = (monaco) => {
    // Add SQL keywords and table name suggestions
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

        // Add column suggestions from schema
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

        return {
          suggestions,
        };
      },
    });
  };

  const handleExecute = async () => {
    if (!query.trim()) {
      toast.error("Please enter a SQL query");
      return;
    }

    try {
      const response = await executeSql.mutateAsync(query);
      setResults(response);
      toast.success("Query executed successfully");
    } catch (error) {
      toast.error("Failed to execute query: " + (error as Error).message);
    }
  };

  return (
    <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="grid grid-rows-[auto_1fr] gap-6 h-[calc(100vh-120px)]">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-medium tracking-tight">SQL Query</h2>
            <Button onClick={handleExecute} disabled={executeSql.isPending}>
              <PlayIcon className="mr-2 h-4 w-4" />
              Execute Query
            </Button>
          </div>
          <div className="border rounded-md overflow-hidden min-h-[200px]">
            <Editor
              height="200px"
              defaultLanguage="sql"
              value={query}
              onChange={(value) => setQuery(value || "")}
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
        </div>

        {results && (
          <div className="overflow-auto">
            <ResultsTable results={results} />
          </div>
        )}
      </div>
    </div>
  );
}

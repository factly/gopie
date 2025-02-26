"use client";

import "regenerator-runtime/runtime";
import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { Button } from "@/components/ui/button";
import { PlayIcon, Loader2, Mic, MicOff } from "lucide-react";
import { toast } from "sonner";
import { ResultsTable } from "@/components/dataset/sql/results-table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Textarea } from "@/components/ui/textarea";
import { useNl2Sql } from "@/lib/mutations/dataset/nl2sql";
import { SqlEditor } from "@/components/dataset/sql/sql-editor";
import { useDataset } from "@/lib/queries/dataset/get-dataset";
import SpeechRecognition, {
  useSpeechRecognition,
} from "react-speech-recognition";

declare global {
  interface Window {
    require: ((
      deps: string[],
      callback: (...args: unknown[]) => void,
    ) => void) & {
      config: (config: { paths: Record<string, string> }) => void;
    };
  }
}

const pageVariants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { duration: 0.3 },
  },
};

const fadeInVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.2 },
};

export default function SqlPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const { datasetId, projectId } = React.use(params);
  const [results, setResults] = React.useState<
    Record<string, unknown>[] | null
  >(null);
  const executeSql = useDatasetSql();
  const nl2Sql = useNl2Sql();
  const [queryMode, setQueryMode] = React.useState<"sql" | "natural">(
    "natural",
  );
  const [naturalQuery, setNaturalQuery] = React.useState("");
  const [generatedSql, setGeneratedSql] = React.useState<string>("");

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition();

  const { data: dataset, isLoading: datasetLoading } = useDataset({
    variables: {
      datasetId,
      projectId,
    },
  });

  const [query, setQuery] = React.useState(
    `SELECT * FROM ${dataset?.name} LIMIT 10`,
  );

  React.useEffect(() => {
    setQuery(`SELECT * FROM ${dataset?.name} LIMIT 10`);
    if (dataset?.name && queryMode === "sql") {
      handleExecute();
    }
  }, [dataset, queryMode]);

  React.useEffect(() => {
    if (transcript) {
      setNaturalQuery(transcript);
    }
  }, [transcript]);

  const handleExecute = async () => {
    if (queryMode === "sql") {
      if (!query.trim()) {
        toast.error("Please enter a SQL query");
        return;
      }

      toast.promise(executeSql.mutateAsync(query), {
        loading: "Executing SQL query...",
        success: (response) => {
          setResults(response.data);
          return "Query executed successfully";
        },
        error: (err) => `Failed to execute query: ${err.message}`,
      });
    } else {
      if (!naturalQuery.trim()) {
        toast.error("Please enter your question");
        return;
      }

      const promiseId = toast.loading("Processing your question...");

      try {
        toast.loading("Converting to SQL...", { id: promiseId });
        const sqlQuery = await nl2Sql.mutateAsync({
          query: naturalQuery,
          datasetId: dataset?.name || "",
        });
        setGeneratedSql(sqlQuery.sql);

        toast.loading("Executing generated SQL...", { id: promiseId });
        const response = await executeSql.mutateAsync(sqlQuery.sql);
        setResults(response.data);

        toast.success("Query executed successfully", { id: promiseId });
      } catch (error) {
        toast.error("Failed to process question: " + (error as Error).message, {
          id: promiseId,
        });
      }
    }
  };

  const handleRunGeneratedSql = async () => {
    if (!generatedSql.trim()) {
      toast.error("No SQL query to execute");
      return;
    }

    toast.promise(executeSql.mutateAsync(generatedSql), {
      loading: "Executing SQL query...",
      success: (response) => {
        setResults(response.data);
        return "Query executed successfully";
      },
      error: (err) => `Failed to execute query: ${err.message}`,
    });
  };

  const toggleListening = () => {
    if (listening) {
      SpeechRecognition.stopListening();
    } else {
      resetTranscript();
      SpeechRecognition.startListening({ continuous: true });
    }
  };

  const isPending = executeSql.isPending || nl2Sql.isPending;

  if (datasetLoading) {
    return <div>Loading dataset...</div>;
  }
  if (!dataset) {
    return <div>No dataset found</div>;
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      className="container mx-auto px-4 sm:px-6 lg:px-8"
    >
      <div className="grid grid-rows-[auto_1fr] gap-6 h-[calc(100vh-120px)]">
        <div className="space-y-4">
          <motion.div
            variants={fadeInVariants}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <h2 className="text-2xl font-medium tracking-tight">
                Query Data
              </h2>
              <ToggleGroup
                type="single"
                value={queryMode}
                onValueChange={(value) =>
                  value && setQueryMode(value as "sql" | "natural")
                }
              >
                <ToggleGroupItem value="sql" aria-label="SQL Mode">
                  SQL
                </ToggleGroupItem>
                <ToggleGroupItem
                  value="natural"
                  aria-label="Natural Language Mode"
                >
                  Natural Language
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
            <Button onClick={handleExecute} disabled={isPending}>
              {isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <PlayIcon className="mr-2 h-4 w-4" />
              )}
              {queryMode === "sql" ? "Execute Query" : "Generate Query"}
            </Button>
          </motion.div>

          <motion.div layout className="border rounded-md overflow-hidden">
            <AnimatePresence mode="wait">
              {queryMode === "sql" ? (
                <motion.div key="sql-editor" {...fadeInVariants}>
                  <SqlEditor
                    value={query}
                    onChange={setQuery}
                    schema={dataset.columns}
                    datasetId={dataset.name}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="natural-language"
                  className="p-4 space-y-4"
                  {...fadeInVariants}
                >
                  <div className="relative">
                    <Textarea
                      placeholder="Ask a question about your data..."
                      value={naturalQuery}
                      onChange={(e) => setNaturalQuery(e.target.value)}
                      className="min-h-[120px] text-base leading-relaxed bg-background focus:ring-2 focus:ring-primary/20 border-muted placeholder:text-muted-foreground/50"
                    />
                    {browserSupportsSpeechRecognition && (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="absolute right-2 top-2"
                        onClick={toggleListening}
                      >
                        {listening ? (
                          <MicOff className="h-4 w-4 text-red-500" />
                        ) : (
                          <Mic className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                  </div>
                  <AnimatePresence>
                    {(nl2Sql.isPending || generatedSql) && (
                      <motion.div
                        className="space-y-2"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-muted-foreground">
                            Generated SQL:
                          </p>
                          <Button
                            size="sm"
                            onClick={handleRunGeneratedSql}
                            disabled={executeSql.isPending}
                          >
                            {executeSql.isPending ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <PlayIcon className="mr-2 h-4 w-4" />
                            )}
                            Run SQL
                          </Button>
                        </div>
                        {nl2Sql.isPending ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/30 rounded-md p-4">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Processing your question...
                          </div>
                        ) : (
                          <div className="border rounded-md overflow-hidden bg-muted/5">
                            <SqlEditor
                              value={generatedSql}
                              onChange={setGeneratedSql}
                              schema={dataset.columns}
                              datasetId={dataset.name}
                            />
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        <AnimatePresence>
          {results && (
            <motion.div
              className="flex-1 overflow-auto"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <ResultsTable results={results} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

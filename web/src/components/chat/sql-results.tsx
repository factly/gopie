import { useSqlStore } from "@/lib/stores/sql-store";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Database, Download } from "lucide-react";
import { cn, downloadCsv } from "@/lib/utils";
import { useChatStore } from "@/lib/stores/chat-store";
import { useEffect } from "react";
import { useParams } from "next/navigation";

export function SqlResults() {
  const { results, isOpen, setIsOpen } = useSqlStore();
  const params = useParams();
  const datasetId = params?.datasetId as string;

  // Get the selected chat ID for the current dataset
  const { getSelectedChatForDataset } = useChatStore();
  const { id: selectedChatId } = getSelectedChatForDataset(datasetId);

  const handleDownload = () => {
    if (!results?.data?.length) return;
    downloadCsv(
      results.data,
      `sql_results_${new Date().toISOString().split("T")[0]}.csv`
    );
  };

  // Close results when no chat is selected
  useEffect(() => {
    if (!selectedChatId) {
      setIsOpen(false);
    }
  }, [selectedChatId, setIsOpen]);

  if (!isOpen) return null;

  // Only show results for current chat
  if (results && results.chatId !== selectedChatId) {
    return (
      <div className="flex h-full flex-col bg-muted/50">
        <div className="flex items-center justify-between border-b px-4 py-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium">SQL Results</h3>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setIsOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <ScrollArea className="flex-1 p-4">
          <div className="flex h-full min-h-screen items-center justify-center">
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <Database className="h-12 w-12 opacity-20" />
              <p className="text-sm font-medium">No results for current chat</p>
              <p className="text-xs">Run a query to see results here</p>
            </div>
          </div>
        </ScrollArea>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-muted/50">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium">SQL Results</h3>
          {results?.error ? (
            <span className="text-xs text-destructive">Error</span>
          ) : (
            <span className="text-xs text-muted-foreground">
              {results?.total || 0} rows
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {results?.data && results.data.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleDownload}
              title="Download as CSV"
            >
              <Download className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setIsOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <ScrollArea className="flex-1 p-4">
        <div className="flex h-full min-h-screen items-center justify-center">
          {results?.error ? (
            <div className="w-full rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <p className="text-sm text-destructive">{results.error}</p>
              <pre className="mt-2 text-xs text-muted-foreground">
                {results.query}
              </pre>
            </div>
          ) : results?.data?.length ? (
            <div className="w-full rounded-lg border">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      {Object.keys(results.data[0] || {}).map((key) => (
                        <th
                          key={key}
                          className="border-r px-4 py-2 text-left font-medium last:border-r-0"
                        >
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.data.map((row, i) => (
                      <tr
                        key={i}
                        className={cn(
                          "border-b last:border-b-0",
                          i % 2 === 0 ? "bg-background" : "bg-muted/30"
                        )}
                      >
                        {Object.values(row).map((value, j) => (
                          <td
                            key={j}
                            className="border-r px-4 py-2 last:border-r-0"
                          >
                            {String(value)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <Database className="h-12 w-12 opacity-20" />
              <p className="text-sm font-medium">No data to display yet</p>
              <p className="text-xs">Run a query to see results here</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import { SqlResults } from "./sql-results";
import { VisualizationResults } from "./visualization-results";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Database, BarChart3, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ResultsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ResultsPanel({ isOpen, onClose }: ResultsPanelProps) {
  const { results: sqlResults } = useSqlStore();
  const { paths: visualizationPaths } = useVisualizationStore();

  const hasSqlResults = !!(sqlResults?.data?.length || sqlResults?.error);
  const hasVisualizations = visualizationPaths.length > 0;

  // Determine default tab
  const defaultTab = hasVisualizations ? "visualizations" : "sql";

  if (!isOpen) return null;

  return (
    <div className="flex h-full flex-col bg-muted/50">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium">Results</h3>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <Tabs defaultValue={defaultTab} className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-2 rounded-none bg-background border-b">
          <TabsTrigger
            value="sql"
            className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background data-[state=active]:shadow-none rounded-none"
            disabled={!hasSqlResults}
          >
            <Database className="h-4 w-4 mr-2" />
            SQL Results
            {sqlResults?.total && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({sqlResults.total})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="visualizations"
            className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background data-[state=active]:shadow-none rounded-none"
            disabled={!hasVisualizations}
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            Visualizations
            {visualizationPaths.length > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({visualizationPaths.length})
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="sql"
          className="flex-1 m-0 data-[state=inactive]:hidden"
        >
          <SqlResults />
        </TabsContent>

        <TabsContent
          value="visualizations"
          className="flex-1 m-0 data-[state=inactive]:hidden"
        >
          <VisualizationResults
            paths={visualizationPaths}
            isOpen={true}
            onClose={() => {}} // Don't close individual components, use the main close
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

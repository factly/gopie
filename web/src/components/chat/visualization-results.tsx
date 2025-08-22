import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { BarChart3, Download, ExternalLink } from "lucide-react";
import vegaEmbed from "vega-embed";

interface VegaSpec {
  title?: string;
  [key: string]: unknown;
}

interface VisualizationData {
  path: string;
  spec: VegaSpec | null;
  isLoading: boolean;
  error?: string;
}

interface VisualizationResultsProps {
  paths: string[];
  isOpen: boolean;
}

export function VisualizationResults({
  paths,
  isOpen,
}: VisualizationResultsProps) {
  const [visualizations, setVisualizations] = useState<VisualizationData[]>([]);
  const vizRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Fetch visualization data from S3 paths
  useEffect(() => {
    if (!paths.length) return;

    const fetchVisualizationData = async () => {
      const vizData: VisualizationData[] = paths.map((path) => ({
        path,
        spec: null,
        isLoading: true,
      }));

      setVisualizations(vizData);

      // Fetch each visualization spec
      for (let i = 0; i < paths.length; i++) {
        try {
          const response = await fetch(paths[i]);
          if (!response.ok) {
            throw new Error(`Failed to fetch: ${response.statusText}`);
          }
          const spec = (await response.json()) as VegaSpec;

          setVisualizations((prev) =>
            prev.map((viz, index) =>
              index === i ? { ...viz, spec, isLoading: false } : viz
            )
          );
        } catch (error) {
          setVisualizations((prev) =>
            prev.map((viz, index) =>
              index === i
                ? {
                    ...viz,
                    isLoading: false,
                    error:
                      error instanceof Error ? error.message : "Unknown error",
                  }
                : viz
            )
          );
        }
      }
    };

    fetchVisualizationData();
  }, [paths]);

  // Render visualizations using vega-embed
  useEffect(() => {
    visualizations.forEach((viz, index) => {
      if (viz.spec && !viz.isLoading && !viz.error && vizRefs.current[index]) {
        // Create a copy of the spec and update schema to match our library version
        const updatedSpec = {
          ...viz.spec,
          $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        };

        const embedOptions = {
          actions: {
            export: true,
            source: false,
            compiled: false,
            editor: false,
          },
          renderer: "svg" as const,
        };

        vegaEmbed(vizRefs.current[index]!, updatedSpec, embedOptions).catch(
          (error) => {
            console.error("Error rendering visualization:", error);
            setVisualizations((prev) =>
              prev.map((v, i) =>
                i === index
                  ? { ...v, error: "Failed to render visualization" }
                  : v
              )
            );
          }
        );
      }
    });
  }, [visualizations]);

  const handleDownloadSpec = (spec: VegaSpec, index: number) => {
    const blob = new Blob([JSON.stringify(spec, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `visualization_${index + 1}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="flex h-full flex-col bg-muted/50">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-6">
          {visualizations.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <BarChart3 className="h-12 w-12 opacity-20" />
              <p className="text-sm font-medium">
                No visualizations to display
              </p>
              <p className="text-xs">
                Visualizations will appear here when generated
              </p>
            </div>
          ) : (
            visualizations.map((viz, index) => (
              <div
                key={viz.path}
                className="border bg-background p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium">
                    {viz.spec?.title || `Visualization ${index + 1}`}
                  </h4>
                  <div className="flex gap-1">
                    {viz.spec && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleDownloadSpec(viz.spec!, index)}
                        title="Download specification"
                      >
                        <Download className="h-3 w-3" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => window.open(viz.path, "_blank")}
                      title="Open source"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                {viz.isLoading ? (
                  <div className="flex items-center justify-center h-64 bg-muted/30">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <div className="h-4 w-4 animate-spin border-2 border-current border-t-transparent" />
                      Loading visualization...
                    </div>
                  </div>
                ) : viz.error ? (
                  <div className="p-4 border border-destructive/50 bg-destructive/10">
                    <p className="text-sm text-destructive font-medium">
                      Error loading visualization
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {viz.error}
                    </p>
                  </div>
                ) : (
                  <div className="h-[400px]">
                    <div
                      ref={(el) => {
                        vizRefs.current[index] = el;
                      }}
                      className="w-full h-full"
                    />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

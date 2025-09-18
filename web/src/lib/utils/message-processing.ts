// Utility functions for processing chat message parts

type MessagePart = {
  type: string;
  [key: string]: unknown;
};

interface ProcessedMessageData {
  datasets: string[];
  sqlQueries: string[];
  intermediateMessages: string[];
  visualizationPaths: string[];
  visualizationResults: string[];
  projectIds: string[];
  datasetIds: string[];
}

export function processMessageParts(parts: unknown): ProcessedMessageData {
  const result: ProcessedMessageData = {
    datasets: [],
    sqlQueries: [],
    intermediateMessages: [],
    visualizationPaths: [],
    visualizationResults: [],
    projectIds: [],
    datasetIds: [],
  };

  if (!Array.isArray(parts)) {
    return result;
  }

  for (const part of parts as MessagePart[]) {
    // Handle the new data part format for AI SDK v5
    if (typeof part.type === "string") {
      // Handle data parts with the new format
      switch (part.type) {
        case "data-sql-query":
          if (part.data && typeof part.data === 'object') {
            const sqlData = part.data as { query?: string };
            if (sqlData.query && !result.sqlQueries.includes(sqlData.query)) {
              result.sqlQueries.push(sqlData.query);
            }
          }
          break;

        case "data-datasets-used":
          if (part.data && typeof part.data === 'object') {
            const datasetsData = part.data as { datasets?: string[] };
            if (datasetsData.datasets && Array.isArray(datasetsData.datasets)) {
              datasetsData.datasets.forEach((dataset: string) => {
                if (!result.datasets.includes(dataset)) {
                  result.datasets.push(dataset);
                }
              });
            }
          }
          break;

        case "data-visualization":
          if (part.data && typeof part.data === 'object') {
            const vizData = part.data as { paths?: string[] };
            if (vizData.paths && Array.isArray(vizData.paths)) {
              vizData.paths.forEach((path: string) => {
                if (!result.visualizationResults.includes(path)) {
                  result.visualizationResults.push(path);
                  result.visualizationPaths.push(path);
                }
              });
            }
          }
          break;

        case "data-intermediate-thought":
          if (part.data && typeof part.data === 'object') {
            const thoughtData = part.data as { content?: string };
            if (thoughtData.content) {
              result.intermediateMessages.push(thoughtData.content);
            }
          }
          break;

        case "data-context-info":
          if (part.data && typeof part.data === 'object') {
            const contextData = part.data as { projectIds?: string[]; datasetIds?: string[] };
            if (contextData.projectIds && Array.isArray(contextData.projectIds)) {
              result.projectIds.push(...contextData.projectIds);
            }
            if (contextData.datasetIds && Array.isArray(contextData.datasetIds)) {
              result.datasetIds.push(...contextData.datasetIds);
            }
          }
          break;

        // Handle legacy tool-invocation parts for backward compatibility
        case "tool-invocation":
          if ("toolInvocation" in part && part.toolInvocation) {
            const toolInvocation = part.toolInvocation as { toolName: string; args: Record<string, unknown> };
            const { toolName, args } = toolInvocation;

            switch (toolName) {
              case "set_context":
                if (args.project_ids && Array.isArray(args.project_ids)) {
                  result.projectIds.push(...args.project_ids);
                }
                if (args.dataset_ids && Array.isArray(args.dataset_ids)) {
                  result.datasetIds.push(...args.dataset_ids);
                }
                break;

              case "datasets_used":
                if (args.datasets && Array.isArray(args.datasets)) {
                  args.datasets.forEach((dataset: string) => {
                    if (!result.datasets.includes(dataset)) {
                      result.datasets.push(dataset);
                    }
                  });
                }
                break;

              case "sql_queries":
                if (args.queries) {
                  if (Array.isArray(args.queries)) {
                    result.sqlQueries.push(...args.queries);
                  } else if (typeof args.queries === "string") {
                    result.sqlQueries.push(args.queries);
                  }
                }
                break;

              case "tool_messages":
                if (
                  args.role === "intermediate" &&
                  typeof args.content === "string"
                ) {
                  result.intermediateMessages.push(args.content);
                }
                break;

              case "visualization_paths":
                if (args.paths && Array.isArray(args.paths)) {
                  args.paths.forEach((path: string) => {
                    if (!result.visualizationPaths.includes(path)) {
                      result.visualizationPaths.push(path);
                    }
                  });
                }
                break;

              case "visualization_result":
                if (args.visualization_json_paths && Array.isArray(args.visualization_json_paths)) {
                  args.visualization_json_paths.forEach(
                    ({ json_path }: { json_path: string }) => {
                      if (!result.visualizationResults.includes(json_path)) {
                        result.visualizationResults.push(json_path);
                      }
                    }
                  );
                }
                break;
            }
          }
          break;
      }
    }
  }

  return result;
}
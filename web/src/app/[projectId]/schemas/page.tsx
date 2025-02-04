"use client";

import * as React from "react";
import ReactFlow, {
  Background,
  Controls,
  Panel,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  Connection,
  addEdge,
} from "reactflow";
import "reactflow/dist/style.css";

import { useSchemas } from "@/lib/queries/dataset/get-schema";
import { SchemaNode } from "@/components/schema/schema-node";
import { Skeleton } from "@/components/ui/skeleton";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";

const nodeTypes = {
  schema: SchemaNode,
};

export default function SchemasPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = React.use(params);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const { data: datasets, isLoading: isDatasetsLoading } = useDatasets({
    variables: {
      projectId,
    },
  });

  const { data: schemas, isLoading: isSchemasLoading } = useSchemas({
    variables: {
      datasetIds: datasets?.results.map((dataset) => dataset.name) ?? [],
    },
  });

  const onConnect = React.useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            animated: true,
            style: { stroke: "hsl(var(--primary))", strokeWidth: 2 },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  React.useEffect(() => {
    if (!schemas) return;

    const newNodes = schemas.map((schema, index) => ({
      id: datasets?.results[index]?.name ?? "",
      type: "schema",
      position: {
        x: (index % 3) * 450 + 200,
        y: Math.floor(index / 3) * 350 + 100,
      },
      data: {
        label: datasets?.results[index]?.name ?? "",
        schema, // Pass the full column info
      },
    }));

    setNodes(newNodes);
  }, [datasets, schemas, setNodes]);

  if (isDatasetsLoading || isSchemasLoading) {
    return <Skeleton className="h-screen w-full" />;
  }

  return (
    <div className="h-[calc(100vh-57px-41px)]">
      {" "}
      {/* Adjust height to account for navbar and tabs */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{
          padding: 0.2, // Add some padding around the nodes
          maxZoom: 1.5, // Limit max zoom level
        }}
        minZoom={0.1} // Allow zooming out further
        maxZoom={2} // Limit max zoom
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
      >
        <Background />
        <Controls position="bottom-right" />{" "}
        {/* Move controls to bottom-right */}
        <Panel position="top-left" className="font-medium m-4">
          Schema Relationships
        </Panel>
      </ReactFlow>
    </div>
  );
}

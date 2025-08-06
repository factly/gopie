"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";
import { Loader2, Database, FolderOpen, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface DatasetPageProps {
  params: Promise<{ datasetId: string }>;
}

export default function DatasetPage({ params }: DatasetPageProps) {
  const router = useRouter();
  const [datasetId, setDatasetId] = useState<string>("");
  const { data: projects, isLoading: projectsLoading, isError: projectsError } = useProjects({});
  const { data: dataset, isLoading: datasetLoading, isError: datasetError } = useDatasetById({
    variables: { datasetId },
    enabled: !!datasetId
  });

  useEffect(() => {
    const setParams = async () => {
      const resolvedParams = await params;
      setDatasetId(resolvedParams.datasetId);
    };
    setParams();
  }, [params]);

  const handleProjectSelect = (projectId: string) => {
    router.push(`/projects/${projectId}/datasets/${datasetId}`);
  };

  const isLoading = projectsLoading || datasetLoading;
  const hasError = projectsError || datasetError;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex items-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  if (hasError || !projects || projects.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-2">Error</h1>
          <p className="text-muted-foreground">
            {projectsError ? "Unable to load projects" : "No projects found"}
          </p>
          <Button 
            variant="outline" 
            className="mt-4" 
            onClick={() => router.push("/")}
          >
            Go Home
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container max-w-4xl mx-auto p-6">
      <div className="space-y-6">
        {/* Dataset Info Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            <h1 className="text-2xl font-semibold">
              {dataset ? dataset.alias || dataset.name : `Dataset ${datasetId.slice(0, 8)}...`}
            </h1>
          </div>
          {dataset && (
            <p className="text-muted-foreground">
              {dataset.description || "No description available"}
            </p>
          )}
        </div>

        {/* Project Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Choose Project Context</CardTitle>
            <CardDescription>
              Select a project to view this dataset within its context. This will help you access the dataset with the appropriate project settings and permissions.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              {projects.map((project) => (
                <Button
                  key={project.id}
                  variant="outline"
                  className="justify-between h-auto p-4 text-left"
                  onClick={() => handleProjectSelect(project.id)}
                >
                  <div className="flex items-center gap-3">
                    <FolderOpen className="h-4 w-4" />
                    <div>
                      <div className="font-medium">{project.name}</div>
                      {project.description && (
                        <div className="text-sm text-muted-foreground">
                          {project.description}
                        </div>
                      )}
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Back to Home */}
        <div className="text-center">
          <Button 
            variant="ghost" 
            onClick={() => router.push("/")}
            className="text-muted-foreground"
          >
            ← Back to Home
          </Button>
        </div>
      </div>
    </div>
  );
}
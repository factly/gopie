"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { useProjects } from "@/lib/queries/project/list-projects";
import { Skeleton } from "@/components/ui/skeleton";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";
import { ProjectCard } from "@/components/project/project-card";
import { useQueryClient } from "@tanstack/react-query";
import { updateProject } from "@/lib/mutations/project/update-project";
import { deleteProject } from "@/lib/mutations/project/delete-project";
import { useToast } from "@/hooks/use-toast";
import { FolderIcon } from "lucide-react";

export default function HomePage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: projects, isLoading } = useProjects({
    variables: {
      limit: 100,
      page: 1,
    },
  });

  const handleUpdateProject = async (
    projectId: string,
    data: { name: string; description: string; updated_by: string },
  ) => {
    try {
      await updateProject(projectId, data);
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { message?: string } };
      };
      const errorMessage =
        error.response?.data?.message ||
        error.message ||
        "Failed to update project";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
      throw err;
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    try {
      await deleteProject(projectId);
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { message?: string } };
      };
      const errorMessage =
        error.response?.data?.message ||
        error.message ||
        "Failed to delete project";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
      throw err;
    }
  };

  if (isLoading) {
    return (
      <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex items-center justify-between">
          <Skeleton className="h-12 w-[300px]" />
          <Skeleton className="h-10 w-[200px]" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-[200px] rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 min-h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-center justify-between pt-8">
        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent"
        >
          Projects
        </motion.h1>
        <CreateProjectDialog />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8"
      >
        {projects && projects.results && projects.results.length > 0 ? (
          projects.results.map((project, idx) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
            >
              <ProjectCard
                project={project}
                onUpdate={handleUpdateProject}
                onDelete={handleDeleteProject}
              />
            </motion.div>
          ))
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="col-span-full flex flex-col items-center justify-center h-[calc(100vh-12rem)]"
          >
            <div className="rounded-full bg-muted p-4 mb-4">
              <FolderIcon className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium text-foreground mb-2">
              No projects yet
            </h3>
            <p className="text-muted-foreground text-center mb-6">
              Get started by creating your first project
            </p>
            <CreateProjectDialog />
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

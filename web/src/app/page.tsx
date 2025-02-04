"use client";

import { useProjects } from "@/lib/queries/project/list-projects";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { motion } from "framer-motion";
import { FolderIcon } from "lucide-react";
import Link from "next/link";

export default function Home() {
  const { data: projects, isLoading, error } = useProjects();

  if (isLoading) {
    return (
      <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-48" /> {/* Adjusted size */}
          <Skeleton className="h-10 w-[140px]" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-[180px] rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <div>Error loading projects: {error.message}</div>;
  }

  return (
    <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-semibold tracking-tight text-foreground/90">
          Projects
        </h1>
        <CreateProjectDialog />
      </div>

      {projects?.results.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[400px] py-16 space-y-4">
          <div className="p-4 rounded-full bg-muted">
            <FolderIcon className="w-8 h-8 text-muted-foreground" />
          </div>
          <h2 className="text-2xl font-medium text-foreground/80">
            No projects yet
          </h2>
          <p className="text-base text-muted-foreground">
            Create your first project to get started
          </p>
          <CreateProjectDialog />
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {projects?.results.map((project, index) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Link
                href={`/${project.id}`}
                className="block group relative overflow-hidden rounded-lg border bg-card text-card-foreground shadow-sm transition-all hover:shadow-md hover:bg-muted/50"
              >
                <div className="p-6">
                  <div className="flex flex-col space-y-3">
                    <h2 className="text-2xl font-medium tracking-tight text-foreground/90">
                      {project.name}
                    </h2>
                    {project.description && (
                      <p className="text-base text-muted-foreground/90 line-clamp-2">
                        {project.description}
                      </p>
                    )}
                    <div className="mt-4 flex items-center text-sm font-medium text-muted-foreground/75">
                      <FolderIcon className="mr-2 h-4 w-4" />
                      {project?.datasetCount ?? 0} datasets
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}

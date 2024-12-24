import { STORAGE_KEYS } from "@/lib/constants";
import { Project } from "@/types/project";
import { createQuery } from "react-query-kit";

async function fetchProject({
  projectId,
}: {
  projectId: string;
}): Promise<Project> {
  try {
    const projects = JSON.parse(
      localStorage.getItem(STORAGE_KEYS.PROJECTS) || "[]"
    ) as Project[];

    const project = projects.find((p) => p.id === projectId);
    if (!project) {
      throw new Error("Project not found");
    }

    return project;
  } catch (error) {
    throw new Error("Failed to fetch project" + error);
  }
}

export const useProject = createQuery({
  queryKey: ["project"],
  fetcher: fetchProject,
});

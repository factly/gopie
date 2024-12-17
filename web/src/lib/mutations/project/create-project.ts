import { createMutation } from "react-query-kit";

import { Project, ProjectInput } from "@/types/project";
import { STORAGE_KEYS } from "@/lib/constants";

async function createProject(project: ProjectInput): Promise<Project> {
  try {
    const newProject: Project = {
      ...project,
      id: crypto.randomUUID(),
      datasets: [],
    };
    const projects = localStorage.getItem(STORAGE_KEYS.PROJECTS);
    const updatedProjects = projects
      ? [...JSON.parse(projects), newProject]
      : [newProject];

    localStorage.setItem(
      STORAGE_KEYS.PROJECTS,
      JSON.stringify(updatedProjects),
    );

    return newProject;
  } catch (error) {
    console.error("Error creating project:", error);
    throw error;
  }
}

export const useCreateProject = createMutation({
  mutationKey: ["create-project"],
  mutationFn: createProject,
});

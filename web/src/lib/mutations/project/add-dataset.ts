import { createMutation } from "react-query-kit";
import { STORAGE_KEYS } from "@/lib/constants";
import { Project } from "@/types/project";

export const useAddDatasetToProject = createMutation({
  mutationKey: ["add-dataset-to-project"],
  mutationFn: async ({
    projectId,
    datasetId,
  }: {
    projectId: string;
    datasetId: string;
  }) => {
    // Fetch the project from the local storage
    const projects = JSON.parse(
      localStorage.getItem(STORAGE_KEYS.PROJECTS) || "[]",
    ) as Project[];
    const project = projects.find((p) => p.id === projectId);

    if (!project) {
      throw new Error("Project not found");
    }

    // Add the dataset to the project
    project.datasets = [...project.datasets, datasetId];

    // Update the project in the local storage
    const updatedProjects = projects.map((p) =>
      p.id === projectId ? project : p,
    );
    localStorage.setItem(
      STORAGE_KEYS.PROJECTS,
      JSON.stringify(updatedProjects),
    );

    return project;
  },
});

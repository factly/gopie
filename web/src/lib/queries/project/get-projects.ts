import { createQuery } from "react-query-kit";
import { STORAGE_KEYS } from "@/lib/constants";
import { Projects } from "@/types/project";

async function fetchProjects(): Promise<Projects> {
  try {
    const projects = localStorage.getItem(STORAGE_KEYS.PROJECTS);
    if (!projects) {
      return [];
    }

    return JSON.parse(projects) as Projects;
  } catch (error) {
    console.error("Error fetching projects:", error);
    return [];
  }
}

export const useProjects = createQuery({
  queryKey: ["projects"],
  fetcher: fetchProjects,
});

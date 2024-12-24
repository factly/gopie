export type Project = {
  id: string;
  name: string;
  description?: string;
  datasets: string[];
};

export type ProjectInput = {
  name: string;
  description?: string;
};

export type Projects = Project[];

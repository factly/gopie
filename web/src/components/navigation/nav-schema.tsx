"use client";

import {
  DatabaseIcon,
  HashIcon,
  CalendarIcon,
  TextIcon,
  TimerIcon,
  TypeIcon,
  ListIcon,
  CircleDotIcon,
} from "lucide-react";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
} from "@/components/ui/sidebar";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";

export function NavSchema() {
  const params = useParams();
  const projectId = params?.projectId as string;
  const datasetId = params?.datasetId as string;

  const { data: datasets } = useDatasets({
    variables: {
      projectId,
    },
    enabled: Boolean(projectId),
  });

  const schema = datasets?.results?.find((d) => d.id === datasetId)?.columns;

  const getColumnIcon = (type: string) => {
    const iconClass = "h-3.5 w-3.5";
    type = type.toLowerCase();
    if (
      type.includes("int") ||
      type.includes("decimal") ||
      type.includes("numeric") ||
      type.includes("float")
    ) {
      return <HashIcon className={iconClass} />;
    }
    if (type.includes("date") || type.includes("timestamp")) {
      return <CalendarIcon className={iconClass} />;
    }
    if (type.includes("time")) {
      return <TimerIcon className={iconClass} />;
    }
    if (
      type.includes("char") ||
      type.includes("text") ||
      type.includes("string")
    ) {
      return <TextIcon className={iconClass} />;
    }
    if (type.includes("bool")) {
      return <CircleDotIcon className={iconClass} />;
    }
    if (type.includes("array") || type.includes("list")) {
      return <ListIcon className={iconClass} />;
    }
    return <TypeIcon className={iconClass} />;
  };

  if (!datasetId || !schema) {
    return null;
  }

  return (
    <SidebarGroup className="group-data-[collapsible=icon]:hidden">
      <SidebarGroupLabel className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          Schema
        </span>
        <DatabaseIcon className="h-3.5 w-3.5 text-muted-foreground" />
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <ScrollArea className="h-[150px] pr-2">
          <div className="space-y-0.5">
            {schema.map((column) => (
              <div
                key={column.column_name}
                className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <div className="text-muted-foreground/70 group-hover:text-muted-foreground/90 transition-colors">
                    {getColumnIcon(column.column_type)}
                  </div>
                  <span className="truncate font-medium text-muted-foreground/90 group-hover:text-foreground transition-colors">
                    {column.column_name}
                  </span>
                </div>
                <Badge
                  variant="outline"
                  className="bg-muted/30 hover:bg-muted border-muted-foreground/20 text-muted-foreground/70 group-hover:text-muted-foreground/90 transition-colors text-[10px] h-4 font-normal"
                >
                  {column.column_type}
                </Badge>
              </div>
            ))}
          </div>
        </ScrollArea>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

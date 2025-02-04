import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TableIcon } from "lucide-react";
import Link from "next/link";
import { Dataset } from "@/lib/api-client";

interface DatasetCardProps {
  dataset: Dataset;
  projectId: string;
}

export function DatasetCard({ dataset, projectId }: DatasetCardProps) {
  return (
    <Link href={`/${projectId}/${dataset.name}`}>
      <Card className="group hover:shadow-md transition-all">
        <CardHeader className="space-y-1">
          <div className="flex items-start justify-between">
            <CardTitle className="text-xl font-semibold line-clamp-1">
              {dataset.name}
            </CardTitle>
            <Badge variant="secondary" className="ml-2">
              CSV
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <TableIcon className="h-4 w-4" />
            <span>Dataset</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

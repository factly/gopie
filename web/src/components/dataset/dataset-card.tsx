import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MoreHorizontal, TableIcon, Trash } from "lucide-react";
import Link from "next/link";
import { Dataset } from "@/lib/api-client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useState } from "react";

interface DatasetCardProps {
  dataset: Dataset;
  projectId: string;
  onDelete?: (datasetId: string) => Promise<void>;
}

export function DatasetCard({
  dataset,
  projectId,
  onDelete,
}: DatasetCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(dataset.id);
    } finally {
      setIsDeleting(false);
    }
  };
  return (
    <Card className="group hover:shadow-md transition-all">
      <CardHeader className="space-y-1">
        <div className="flex items-start justify-between">
          <Link href={`/${projectId}/${dataset.id}`}>
            <CardTitle className="text-xl font-semibold line-clamp-1">
              {dataset.alias || dataset.name}
            </CardTitle>
          </Link>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="ml-2">
              CSV
            </Badge>
            {onDelete && (
              <AlertDialog>
                <DropdownMenu modal={false}>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <AlertDialogTrigger asChild>
                      <DropdownMenuItem className="text-red-500">
                        <Trash className="h-4 w-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </AlertDialogTrigger>
                  </DropdownMenuContent>
                </DropdownMenu>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete the dataset &quot;
                      {dataset.id}&quot;. This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleDelete}
                      disabled={isDeleting}
                      className="bg-red-500 hover:bg-red-600"
                    >
                      {isDeleting ? "Deleting..." : "Delete"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        </div>
        {dataset.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {dataset.description}
          </p>
        )}
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <TableIcon className="h-4 w-4" />
          <span>Dataset</span>
        </div>
      </CardContent>
    </Card>
  );
}

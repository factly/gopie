import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  MoreHorizontal,
  Trash,
  Calendar,
  MessageSquare,
  TableIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
} from "@/components/ui/alert-dialog";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

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
  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDelete = async (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    if (!onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(dataset.id);
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  // Function to create a simple initial avatar from dataset name
  // const getInitialAvatar = (name: string) => {
  //   return name.charAt(0).toUpperCase();
  // };

  const preventLinkNavigation = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleChatClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Create context data for this dataset
    const contextData = encodeURIComponent(
      JSON.stringify([
        {
          id: dataset.id,
          type: "dataset",
          name: dataset.alias || dataset.name,
          projectId: projectId,
        },
      ])
    );

    router.push(`/chat?contextData=${contextData}`);
  };

  return (
    <Link
      href={`/projects/${projectId}/datasets/${dataset.id}`}
      className="block"
    >
      <Card
        className={cn(
          "group transition-all duration-300 relative overflow-hidden border border-border/40 hover:border-border/80",
          "backdrop-blur-sm bg-card/80 hover:bg-card/90",
          "hover:shadow-lg hover:shadow-primary/5",
          "cursor-pointer"
        )}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div
          className={cn(
            "absolute top-0 right-0 w-[50px] h-[50px] bg-gradient-to-br from-primary/10 to-primary/5",
            "transition-all duration-300 ease-in-out",
            isHovered ? "opacity-100" : "opacity-50"
          )}
        />

        <CardHeader className="pb-2">
          {/* Title section with right padding for chat icon */}
          <div className="flex items-start justify-between pr-[60px] mb-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              {/* <div className="flex-shrink-0 w-10 h-10  bg-primary/10 text-primary flex items-center justify-center font-medium select-none">
                {getInitialAvatar(dataset.alias || dataset.name)}
              </div> */}
              <div className="min-w-0 flex-1">
                <CardTitle className="text-xl font-semibold line-clamp-1 group-hover:text-primary transition-colors break-words">
                  {dataset.alias || dataset.name}
                </CardTitle>
              </div>
            </div>
          </div>

          {/* Description section using full width */}
          <div className="h-[40px]">
            {dataset.description ? (
              <p className="text-sm text-muted-foreground line-clamp-2 break-words">
                {dataset.description}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground opacity-0">&nbsp;</p>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="absolute top-0 right-0 h-[50px] w-[50px] p-0 z-10"
            onClick={handleChatClick}
          >
            <MessageSquare className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="mt-2 pt-3 border-t border-border/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <TableIcon className="h-3.5 w-3.5" />
                  <span className="font-medium">
                    {new Intl.NumberFormat("en", {
                      notation: "compact",
                    }).format(dataset.row_count || 0)}
                  </span>
                </div>

                {dataset.created_at && (
                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>
                      {format(new Date(dataset.created_at), "MMM d, yyyy")}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                {onDelete && (
                  <>
                    <DropdownMenu modal={false}>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={preventLinkNavigation}
                        >
                          <MoreHorizontal className="h-3 w-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent
                        align="end"
                        onClick={preventLinkNavigation}
                      >
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => {
                            preventLinkNavigation(e);
                            setShowDeleteDialog(true);
                          }}
                        >
                          <Trash className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>

                    <AlertDialog
                      open={showDeleteDialog}
                      onOpenChange={setShowDeleteDialog}
                    >
                      <AlertDialogContent onClick={preventLinkNavigation}>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently delete the dataset &quot;
                            {dataset.alias || dataset.name}&quot;. This action
                            cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel onClick={preventLinkNavigation}>
                            Cancel
                          </AlertDialogCancel>
                          <AlertDialogAction
                            onClick={(e) => handleDelete(e)}
                            disabled={isDeleting}
                            className="bg-destructive hover:bg-destructive/90"
                          >
                            {isDeleting ? "Deleting..." : "Delete"}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </>
                )}

                <div
                  className={cn(
                    "flex items-center gap-1 text-xs font-medium text-primary opacity-0 transform translate-x-2",
                    "transition-all duration-300 ease-in-out",
                    isHovered ? "opacity-100 translate-x-0" : ""
                  )}
                >
                  {/* <span>View</span>
                  <ChevronRight className="h-3 w-3" /> */}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

"use client";

import { useState } from "react";
import { useListDownloads } from "@/lib/queries/download/list-downloads";
import { useDeleteDownload } from "@/lib/mutations/download/delete-download";
import { Download } from "@/lib/stores/download-store";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";
import { format } from "date-fns";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DownloadIcon,
  TrashIcon,
  ExternalLinkIcon,
  FileIcon,
  AlertCircleIcon,
  CheckCircleIcon,
  ClockIcon,
  Loader2Icon,
} from "lucide-react";
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
import { useToast } from "@/hooks/use-toast";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// Component to display dataset details with SQL query
function DatasetDetails({ datasetId, sql }: { datasetId: string; sql?: string }) {
  const { data: dataset, isLoading } = useDatasetById({ 
    variables: { datasetId },
    enabled: !!datasetId
  });

  if (isLoading) {
    return (
      <div className="max-w-[400px]">
        <Skeleton className="h-4 w-[200px] mb-1" />
        <Skeleton className="h-3 w-[150px]" />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="max-w-[400px]">
        <p className="font-medium truncate text-muted-foreground">
          Dataset not found
        </p>
        <p className="text-xs text-muted-foreground truncate">
          ID: {datasetId}
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-[400px]">
      <p className="font-medium truncate" title={dataset.alias}>
        {dataset.alias}
      </p>
      <p className="text-xs text-muted-foreground truncate" title={dataset.description || dataset.name}>
        {dataset.description || dataset.name}
      </p>
      {sql && (
        <p className="text-xs text-muted-foreground truncate mt-1" title={sql}>
          Query: {sql}
        </p>
      )}
    </div>
  );
}

export default function DownloadsPage() {
  const { toast } = useToast();
  const [page, setPage] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedDownload, setSelectedDownload] = useState<Download | null>(null);
  const limit = 20;

  const { data: downloads, isLoading, refetch } = useListDownloads({
    limit,
    offset: page * limit,
  });

  const deleteDownloadMutation = useDeleteDownload();

  const handleDelete = async () => {
    if (!selectedDownload) return;

    try {
      await deleteDownloadMutation.mutateAsync(selectedDownload.id);
      toast({
        title: "Download deleted",
        description: "The download has been deleted successfully.",
      });
      refetch();
    } catch {
      toast({
        title: "Error",
        description: "Failed to delete download",
        variant: "destructive",
      });
    } finally {
      setDeleteDialogOpen(false);
      setSelectedDownload(null);
    }
  };

  const handleDownloadClick = (download: Download) => {
    if (download.status !== 'completed' || !download.pre_signed_url) {
      toast({
        title: "Download not ready",
        description: "This download is not yet completed or the link has expired.",
        variant: "destructive",
      });
      return;
    }

    // Check if URL has expired
    if (download.expires_at && new Date(download.expires_at) < new Date()) {
      toast({
        title: "Download expired",
        description: "This download link has expired. Please create a new download.",
        variant: "destructive",
      });
      return;
    }

    window.open(download.pre_signed_url, '_blank');
  };

  const getStatusBadge = (status: Download['status']) => {
    switch (status) {
      case 'completed':
        return (
          <Badge variant="default" className="gap-1">
            <CheckCircleIcon className="h-3 w-3" />
            Completed
          </Badge>
        );
      case 'processing':
        return (
          <Badge variant="secondary" className="gap-1">
            <Loader2Icon className="h-3 w-3 animate-spin" />
            Processing
          </Badge>
        );
      case 'pending':
        return (
          <Badge variant="secondary" className="gap-1">
            <ClockIcon className="h-3 w-3" />
            Pending
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="destructive" className="gap-1">
            <AlertCircleIcon className="h-3 w-3" />
            Failed
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format.toLowerCase()) {
      case 'csv':
        return <FileIcon className="h-4 w-4 text-green-600" />;
      case 'json':
        return <FileIcon className="h-4 w-4 text-blue-600" />;
      case 'parquet':
        return <FileIcon className="h-4 w-4 text-purple-600" />;
      default:
        return <FileIcon className="h-4 w-4" />;
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Downloads</CardTitle>
            <CardDescription>Manage your dataset downloads</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-[250px]" />
                    <Skeleton className="h-4 w-[200px]" />
                  </div>
                  <Skeleton className="h-8 w-[100px]" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <Card>
        <CardHeader>
          <CardTitle>Downloads</CardTitle>
          <CardDescription>
            Manage your dataset downloads and export history
          </CardDescription>
        </CardHeader>
        <CardContent>
          {downloads && downloads.length > 0 ? (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Format</TableHead>
                      <TableHead>Dataset</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Expires</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {downloads.map((download) => (
                      <TableRow key={download.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getFormatIcon(download.format)}
                            <span className="font-medium uppercase">
                              {download.format}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <DatasetDetails datasetId={download.dataset_id} sql={download.sql} />
                        </TableCell>
                        <TableCell>{getStatusBadge(download.status)}</TableCell>
                        <TableCell>
                          {format(new Date(download.created_at), "MMM d, yyyy h:mm a")}
                        </TableCell>
                        <TableCell>
                          {download.expires_at ? (
                            <span className={
                              new Date(download.expires_at) < new Date()
                                ? "text-destructive"
                                : "text-muted-foreground"
                            }>
                              {format(new Date(download.expires_at), "MMM d, h:mm a")}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            {download.status === 'completed' && download.pre_signed_url && (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDownloadClick(download)}
                                disabled={
                                  download.expires_at
                                    ? new Date(download.expires_at) < new Date()
                                    : false
                                }
                              >
                                <ExternalLinkIcon className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => {
                                setSelectedDownload(download);
                                setDeleteDialogOpen(true);
                              }}
                            >
                              <TrashIcon className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {downloads.length === limit && (
                <div className="mt-4">
                  <Pagination>
                    <PaginationContent>
                      <PaginationItem>
                        <PaginationPrevious
                          onClick={() => setPage(Math.max(0, page - 1))}
                          className={page === 0 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                        />
                      </PaginationItem>
                      <PaginationItem>
                        <PaginationLink>{page + 1}</PaginationLink>
                      </PaginationItem>
                      <PaginationItem>
                        <PaginationNext
                          onClick={() => setPage(page + 1)}
                          className="cursor-pointer"
                        />
                      </PaginationItem>
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <DownloadIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No downloads yet</h3>
              <p className="text-muted-foreground">
                Your download history will appear here once you export datasets.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Download</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this download? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

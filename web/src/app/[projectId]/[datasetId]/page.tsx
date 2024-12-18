"use client";

import * as React from "react";
import { TableIcon, DownloadIcon, FileSpreadsheetIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export default function DatasetPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const { projectId, datasetId } = React.use(params);
  // TODO: Add query to fetch dataset details

  return (
    <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Dataset Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-semibold tracking-tight text-foreground/90">
              {datasetId}
            </h1>
            <Badge variant="secondary" className="h-6">
              CSV
            </Badge>
          </div>
          <p className="text-lg text-muted-foreground/90">
            Dataset information and preview
          </p>
        </div>
        <Button variant="outline" size="sm" className="h-9">
          <DownloadIcon className="mr-2 h-4 w-4" />
          Download Dataset
        </Button>
      </div>

      {/* Dataset Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Rows
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,234</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Columns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              File Size
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.4 MB</div>
          </CardContent>
        </Card>
      </div>

      {/* Data Preview */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-medium tracking-tight">Data Preview</h2>
          <Badge variant="outline" className="h-6">
            <FileSpreadsheetIcon className="mr-2 h-4 w-4" />
            First 100 rows
          </Badge>
        </div>
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Column 1</TableHead>
                <TableHead>Column 2</TableHead>
                <TableHead>Column 3</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...Array(5)].map((_, i) => (
                <TableRow key={i}>
                  <TableCell>Value 1</TableCell>
                  <TableCell>Value 2</TableCell>
                  <TableCell>Value 3</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}

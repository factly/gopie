import { Handle, Position } from "reactflow";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { KeyIcon, TableIcon } from "lucide-react";
import type { ColumnInfo } from "@/lib/queries/dataset/get-schema";

interface SchemaNodeProps {
  data: {
    label: string;
    schema: {
      schema: ColumnInfo[];
    };
  };
}

export function SchemaNode({ data }: SchemaNodeProps) {
  const primaryKeys = data.schema.schema.filter((field) => field.key === "PRI");
  const regularFields = data.schema.schema.filter(
    (field) => field.key !== "PRI"
  );

  return (
    <Card className="w-[400px] shadow-lg">
      <CardHeader className="p-3 border-b bg-muted/50 rounded-t-lg">
        <CardTitle className="flex items-center gap-2 text-sm">
          <TableIcon className="h-4 w-4 text-muted-foreground" />
          <Badge variant="outline" className="font-mono px-2 py-0.5">
            {data.label}
          </Badge>
          <Badge
            variant="secondary"
            className="ml-auto text-[10px] font-normal"
          >
            {data.schema.schema.length} columns
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {primaryKeys.length > 0 && (
          <div className="border-b bg-primary/5 divide-y divide-primary/10">
            {primaryKeys.map((field) => (
              <FieldRow key={field.column_name} field={field} isPrimary />
            ))}
          </div>
        )}
        <div className="divide-y rounded-b-lg overflow-hidden">
          {regularFields.map((field, index) => (
            <FieldRow
              key={field.column_name}
              field={field}
              isLast={index === regularFields.length - 1}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function FieldRow({
  field,
  isPrimary = false,
  isLast = false,
}: {
  field: ColumnInfo;
  isPrimary?: boolean;
  isLast?: boolean;
}) {
  return (
    <div
      className={cn(
        "group flex items-center gap-2 pl-8 pr-3 py-2 hover:bg-muted/50 relative",
        isPrimary && "hover:bg-primary/10",
        isLast && "rounded-b-lg"
      )}
    >
      <Handle
        type="source"
        position={Position.Left}
        id={field.column_name}
        className={cn(
          "w-3 h-3 border-2 !bg-background z-10",
          "opacity-0 group-hover:opacity-100",
          isPrimary && "!border-primary"
        )}
        style={{
          left: 8,
          top: "50%",
          transform: "translateY(-50%)",
        }}
      />
      <div className="flex items-center gap-1.5 min-w-[140px] font-medium">
        {isPrimary && <KeyIcon className="h-3 w-3 text-primary shrink-0" />}
        <span className="font-mono truncate">{field.column_name}</span>
      </div>
      <div className="flex items-center gap-2 text-muted-foreground overflow-hidden">
        <Badge
          variant={isPrimary ? "default" : "outline"}
          className={cn(
            "font-mono text-[10px] px-1.5 py-0 h-5 shrink-0",
            field.null === "YES" && "border-dashed opacity-80"
          )}
        >
          {field.column_type}
        </Badge>
        <div className="flex items-center gap-1.5 text-muted-foreground/70 overflow-hidden">
          {field.null === "YES" && (
            <Badge variant="secondary" className="text-[10px] h-5">
              nullable
            </Badge>
          )}
          {field.default && (
            <span className="font-mono text-[10px] truncate">
              default: {field.default}
            </span>
          )}
          {field.extra && (
            <Badge variant="secondary" className="text-[10px] h-5">
              {field.extra}
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

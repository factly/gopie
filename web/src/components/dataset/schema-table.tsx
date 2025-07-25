import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ColumnInfo } from "@/lib/queries/dataset/get-schema";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";

const MotionTableBody = motion.create(TableBody);
const MotionTableRow = motion.create(TableRow);

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export function SchemaTable({ schema }: { schema: ColumnInfo[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-background">
          <TableHead className="w-[200px]">Column Name</TableHead>
          <TableHead className="w-[200px]">Data Type</TableHead>
          <TableHead className="w-[100px]">Nullable</TableHead>
          <TableHead>Default Value</TableHead>
          <TableHead className="w-[100px]">Key</TableHead>
          <TableHead>Extra</TableHead>
        </TableRow>
      </TableHeader>
      <MotionTableBody variants={container} initial="hidden" animate="show">
        {schema.map((column) => (
          <MotionTableRow
            key={column.column_name}
            variants={item}
            className="group transition-colors"
          >
            <TableCell className="font-medium">
              <motion.div transition={{ duration: 0.2 }}>
                {column.column_name}
              </motion.div>
            </TableCell>
            <TableCell>
              <code className="px-2 py-1 bg-muted text-sm">
                {column.column_type}
              </code>
            </TableCell>
            <TableCell>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Badge
                  variant={column.null === "YES" ? "secondary" : "destructive"}
                  className="font-medium transition-colors"
                >
                  {column.null === "YES" ? "NULL" : "NOT NULL"}
                </Badge>
              </motion.div>
            </TableCell>
            <TableCell>
              {column.default === null ? (
                <span className="text-muted-foreground italic">null</span>
              ) : (
                <code className="px-2 py-1 bg-muted text-sm">
                  {column.default}
                </code>
              )}
            </TableCell>
            <TableCell>
              {column.key ? (
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Badge
                    variant="outline"
                    className="font-medium transition-colors"
                  >
                    {column.key}
                  </Badge>
                </motion.div>
              ) : (
                "-"
              )}
            </TableCell>
            <TableCell>{column.extra || "-"}</TableCell>
          </MotionTableRow>
        ))}
      </MotionTableBody>
    </Table>
  );
}

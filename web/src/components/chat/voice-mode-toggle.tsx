import { Button } from "@/components/ui/button";
import { Headphones } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface VoiceModeToggleProps {
  isActive: boolean;
  onToggle: () => void;
  className?: string;
  variant?: "default" | "outline" | "ghost";
}

export function VoiceModeToggle({
  isActive,
  onToggle,
  className = "",
  variant,
}: VoiceModeToggleProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={isActive ? "default" : variant || "outline"}
          size="icon"
          onClick={onToggle}
          className={`h-11 w-11 shadow-sm ${
            isActive ? "bg-primary text-primary-foreground" : ""
          } ${className}`}
        >
          <Headphones className="h-5 w-5" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        {isActive ? "Disable voice mode" : "Enable voice mode"}
      </TooltipContent>
    </Tooltip>
  );
}

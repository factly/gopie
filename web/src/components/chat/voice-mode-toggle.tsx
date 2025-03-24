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
}

export function VoiceModeToggle({ isActive, onToggle }: VoiceModeToggleProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={isActive ? "default" : "ghost"}
          size="icon"
          onClick={onToggle}
          className={isActive ? "bg-primary text-primary-foreground" : ""}
        >
          <Headphones className="h-4 w-4" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        {isActive ? "Disable voice mode" : "Enable voice mode"}
      </TooltipContent>
    </Tooltip>
  );
}

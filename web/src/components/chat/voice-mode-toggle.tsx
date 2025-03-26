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
          variant={isActive ? "default" : "outline"}
          size="icon"
          onClick={onToggle}
          className={`h-11 w-11 rounded-full shadow-sm ${
            isActive ? "bg-primary text-primary-foreground" : ""
          }`}
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

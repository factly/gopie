"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Share2, Globe, Lock, Building2 } from "lucide-react";
import { ChatVisibility, useUpdateChatVisibility } from "@/lib/mutations/chat";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

interface ShareChatDialogProps {
  chatId: string;
  currentVisibility?: ChatVisibility;
  children?: React.ReactNode;
}

const visibilityOptions = [
  {
    value: "private" as const,
    label: "Private",
    description: "Only you can view this chat",
    icon: Lock,
  },
  {
    value: "organization" as const,
    label: "Organization",
    description: "Anyone in your organization can view this chat",
    icon: Building2,
  },
  {
    value: "public" as const,
    label: "Public",
    description: "Anyone with the link can view this chat",
    icon: Globe,
  },
];

export function ShareChatDialog({
  chatId,
  currentVisibility = "private",
  children,
}: ShareChatDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedVisibility, setSelectedVisibility] =
    useState<ChatVisibility>(currentVisibility);
  const queryClient = useQueryClient();

  const updateVisibility = useUpdateChatVisibility();

  const handleUpdateVisibility = async () => {
    try {
      await updateVisibility.mutateAsync({
        chatId,
        visibility: selectedVisibility,
      });

      // Invalidate chat queries to refresh the data
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      await queryClient.invalidateQueries({
        queryKey: ["chat-details", { chatId }],
      });

      toast.success("Chat visibility updated successfully");
      setOpen(false);
    } catch (error) {
      console.error("Failed to update chat visibility:", error);
      toast.error("Failed to update chat visibility");
    }
  };

  const selectedOption = visibilityOptions.find(
    (option) => option.value === selectedVisibility
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children || (
          <Button variant="ghost" size="sm">
            <Share2 className="h-4 w-4 mr-1" />
            Share
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share Chat</DialogTitle>
          <DialogDescription>
            Choose who can view this chat conversation.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="visibility">Visibility</Label>
            <Select
              value={selectedVisibility}
              onValueChange={(value: ChatVisibility) =>
                setSelectedVisibility(value)
              }
            >
              <SelectTrigger>
                <SelectValue>
                  {selectedOption && (
                    <div className="flex items-center gap-2">
                      <selectedOption.icon className="h-4 w-4" />
                      <span>{selectedOption.label}</span>
                    </div>
                  )}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {visibilityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="flex items-start gap-3">
                      <option.icon className="h-4 w-4 mt-0.5 text-muted-foreground" />
                      <div className="flex flex-col">
                        <span className="font-medium">{option.label}</span>
                        <span className="text-xs text-muted-foreground">
                          {option.description}
                        </span>
                      </div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedVisibility === "public" && (
            <div className="p-3 bg-muted/50 border">
              <div className="flex items-center gap-2 text-sm">
                <Globe className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Public Link</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Anyone with this link will be able to view the chat
                conversation.
              </p>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={updateVisibility.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpdateVisibility}
            disabled={
              updateVisibility.isPending ||
              selectedVisibility === currentVisibility
            }
          >
            {updateVisibility.isPending ? "Updating..." : "Update"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

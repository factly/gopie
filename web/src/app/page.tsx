"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { useProjects } from "@/lib/queries/project/list-projects";
import { Skeleton } from "@/components/ui/skeleton";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";
import { ProjectCard } from "@/components/project/project-card";
import { useQueryClient } from "@tanstack/react-query";
import { updateProject } from "@/lib/mutations/project/update-project";
import { deleteProject } from "@/lib/mutations/project/delete-project";
import { useToast } from "@/hooks/use-toast";
import { FolderIcon } from "lucide-react";
import { ProtectedPage } from "@/components/auth/protected-page";
import { AuthStatus } from "@/components/auth/auth-status";
import { MentionInput } from "@/components/chat/mention-input";
import { ContextPicker, ContextItem } from "@/components/chat/context-picker";
import { useCreateChat } from "@/lib/mutations/chat";
import { useChatStore } from "@/lib/stores/chat-store";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function HomePage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const router = useRouter();
  const {
    data: projects,
    isLoading,
    error,
  } = useProjects({
    variables: {
      limit: 100,
      page: 1,
    },
  });

  // Chat functionality
  const [inputValue, setInputValue] = useState("");
  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);
  const [isSending, setIsSending] = useState(false);
  const createChat = useCreateChat();
  const { selectChat } = useChatStore();

  const handleSelectContext = (context: ContextItem) => {
    setSelectedContexts((prev) => [...prev, context]);
  };

  const handleRemoveContext = (contextId: string) => {
    setSelectedContexts((prev) => prev.filter((c) => c.id !== contextId));
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isSending) return;

    try {
      const success = await sendMessage(inputValue);
      // Only clear input if message was successfully sent
      if (success) {
        setInputValue("");
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      toast({
        title: "Error",
        description: "Failed to send message",
        variant: "destructive",
      });
    }
  };

  const sendMessage = async (message: string) => {
    if (!message.trim() || isSending) return false;

    // Check if there's at least one dataset in the context
    const datasetContext = selectedContexts.find(
      (ctx) => ctx.type === "dataset"
    );
    if (!datasetContext) {
      toast({
        title: "Context Required",
        description:
          "Please select at least one dataset in context before sending a message",
        variant: "destructive",
      });
      return false;
    }

    setIsSending(true);

    try {
      // Redirect to the chat page with the message and context information
      const encodedMessage = encodeURIComponent(message);
      const contextData = encodeURIComponent(JSON.stringify(selectedContexts));
      router.push(
        `/chat?initialMessage=${encodedMessage}&contextData=${contextData}`
      );
      return true;

      // Note: The code below is intentionally not executed due to the return statement above
      // It's kept for reference in case we need to revert to the old behavior

      // Get context information for logs and potential backend use
      if (selectedContexts.length > 0) {
        console.log(
          "Using contexts:",
          selectedContexts.map((ctx) => ({ id: ctx.id, type: ctx.type }))
        );
      }

      // Note: In a home page context, we don't need to specify a dataset ID
      const result = await createChat.mutateAsync({
        messages: [{ role: "user", content: message }],
      });

      // Success notification
      toast({
        title: "Success",
        description: "Your message has been sent",
      });

      // If we get a chatId back, we could navigate to the chat page
      // or handle the response here
      if (result?.data?.id) {
        selectChat(result.data.id, message.substring(0, 40) + "...");

        // Optionally navigate to the chat page
        // router.push(`/${project}/dataset/chat?id=${result.data.id}`);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send message",
        variant: "destructive",
      });
      console.error(error);
    } finally {
      setIsSending(false);
    }
  };

  const handleUpdateProject = async (
    projectId: string,
    data: { name: string; description: string; updated_by: string }
  ) => {
    try {
      await updateProject(projectId, data);
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { message?: string } };
      };
      const errorMessage =
        error.response?.data?.message ||
        error.message ||
        "Failed to update project";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
      throw err;
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    try {
      await deleteProject(projectId);
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });
    } catch (err) {
      const error = err as {
        message?: string;
        response?: { data?: { message?: string } };
      };
      const errorMessage =
        error.response?.data?.message ||
        error.message ||
        "Failed to delete project";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
      throw err;
    }
  };

  const renderContent = () => {
    if (error) {
      return (
        <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              Failed to load projects: {error.message}
            </AlertDescription>
          </Alert>
          <CreateProjectDialog />
        </div>
      );
    }

    if (isLoading) {
      return (
        <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex items-center justify-between">
            <Skeleton className="h-12 w-[300px]" />
            <Skeleton className="h-10 w-[200px]" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-[200px] rounded-lg" />
            ))}
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen flex flex-col">
        {/* Gradient background */}
        <div className="absolute inset-x-0 top-0 h-[300px] bg-gradient-to-br from-purple-600 via-pink-500 to-orange-400 opacity-70 -z-10" />

        {/* Navbar */}
        <div className="border-b bg-background/80 backdrop-blur-sm z-10">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Link href="/" className="flex items-center gap-2">
                <Image
                  src="/gopie.svg"
                  alt="GoPie Logo"
                  width={28}
                  height={28}
                  className="w-7 h-7"
                />
                <span className="font-semibold text-lg">GoPie</span>
              </Link>
            </div>
            <AuthStatus size="md" />
          </div>
        </div>

        <div className="flex-1 container mx-auto px-4 sm:px-6 lg:px-8 flex flex-col">
          {/* Centered Chat Interface */}
          <div className="flex flex-col items-center justify-center min-h-[45vh] py-20">
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-2xl"
            >
              <div className="flex flex-col items-center mb-8">
                <div className="flex items-center mb-4">
                  <Image
                    src="/gopie.svg"
                    alt="GoPie Logo"
                    width={48}
                    height={48}
                    className="w-12 h-12 mr-3"
                  />
                  <h2 className="text-3xl font-semibold">GoPie Chat</h2>
                </div>
                <p className="text-muted-foreground text-center text-base max-w-md mt-2">
                  Your AI-powered assistant for data insights and analysis
                </p>
              </div>

              <div className="rounded-2xl bg-black/10 dark:bg-white/5 p-3 backdrop-blur-sm border border-black/10 dark:border-white/10 shadow-sm">
                <div className="flex items-center gap-2">
                  <ContextPicker
                    selectedContexts={selectedContexts}
                    onSelectContext={handleSelectContext}
                    onRemoveContext={handleRemoveContext}
                    triggerClassName="h-14 w-14 rounded-full bg-transparent text-foreground hover:bg-black/5 dark:hover:bg-white/5"
                  />
                  <MentionInput
                    value={inputValue}
                    onChange={setInputValue}
                    onSubmit={handleSendMessage}
                    disabled={isSending}
                    placeholder="Ask GoPie anything..."
                    selectedContexts={selectedContexts}
                    onSelectContext={handleSelectContext}
                    onRemoveContext={handleRemoveContext}
                    className="flex-1"
                    showSendButton={true}
                    isSending={isSending}
                  />
                </div>
              </div>
            </motion.div>
          </div>

          {/* Projects section pushed to bottom */}
          <div className="mt-16 mb-20">
            <div className="flex items-center justify-between pb-8">
              <motion.h1
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-4xl font-bold tracking-tight"
              >
                Projects
              </motion.h1>
              <CreateProjectDialog />
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
            >
              {projects && projects.results && projects.results.length > 0 ? (
                projects.results.map((project, idx) => (
                  <motion.div
                    key={project.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                  >
                    <ProjectCard
                      project={project}
                      onUpdate={handleUpdateProject}
                      onDelete={handleDeleteProject}
                    />
                  </motion.div>
                ))
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="col-span-full flex flex-col items-center justify-center py-12"
                >
                  <div className="rounded-full bg-muted p-4 mb-4">
                    <FolderIcon className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-medium text-foreground mb-2">
                    No projects yet
                  </h3>
                  <p className="text-muted-foreground text-center mb-6 max-w-md">
                    Start by creating your first project to organize your data
                  </p>
                  <CreateProjectDialog />
                </motion.div>
              )}
            </motion.div>
          </div>
        </div>
      </div>
    );
  };

  return <ProtectedPage>{renderContent()}</ProtectedPage>;
}

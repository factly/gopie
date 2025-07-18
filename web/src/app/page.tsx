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
import { FolderIcon, SettingsIcon } from "lucide-react";
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
import { ThemeToggle } from "@/components/theme/toggle";
// import { UserInfo } from "@/components/dashboard/user-info";

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
  const [isInputFocused, setIsInputFocused] = useState(false);
  const createChat = useCreateChat();
  const { selectChat } = useChatStore();

  const handleSelectContext = (context: ContextItem) => {
    setSelectedContexts((prev) => [...prev, context]);
    // Stop flashing when context is selected
    setIsInputFocused(false);
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

    // Check if there's at least one context item selected (any type)
    if (selectedContexts.length === 0) {
      toast({
        title: "Context Required",
        description:
          "Please select at least one context item before sending a message",
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
              <Skeleton key={i} className="h-[200px]" />
            ))}
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen flex flex-col">
        {/* Gradient background */}
        <div className="absolute inset-x-0 top-0 h-[300px] bg-gradient-to-br from-primary/70 via-primary/60 to-secondary/70 opacity-70 -z-10" />

        {/* Navbar */}
        <div className="border-b bg-background/80 backdrop-blur-sm z-10">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Link href="/" className="flex items-center gap-2">
                <Image
                  src="/GoPie_Logo.svg"
                  alt="GoPie Logo"
                  width={130}
                  height={57}
                  className="h-12 dark:hidden"
                  priority
                />
                <Image
                  src="/GoPie_Logo_Dark.svg"
                  alt="GoPie Logo"
                  width={130}
                  height={57}
                  className="h-12 hidden dark:block"
                  priority
                />
              </Link>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/settings"
                className="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-10 w-10"
              >
                <SettingsIcon className="h-4 w-4" />
                <span className="sr-only">Settings</span>
              </Link>
              <ThemeToggle />
              <AuthStatus size="md" />
            </div>
          </div>
        </div>

        <div className="flex-1 container mx-auto px-4 sm:px-6 lg:px-8 flex flex-col">
          {/* User Info Section */}
          {/* <div className="py-8">
            <UserInfo />
          </div> */}

          {/* Centered Chat Interface */}
          <div className="flex flex-col items-center justify-center min-h-[45vh] py-20">
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-2xl"
            >
              <div className="mb-6">
                <div className="flex justify-center mb-3">
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-background/30 backdrop-blur-sm max-w-md">
                    <a
                      href="https://github.com/factly/gopie"
                      className="text-sm text-muted-foreground hover:text-primary flex items-center gap-1 transition-colors"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-4 w-4"
                      >
                        <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
                        <path d="M9 18c-4.51 2-5-2-7-2" />
                      </svg>
                      Star on GitHub
                    </a>
                  </div>
                </div>
                <h1 className="text-4xl md:text-5xl font-bold text-center text-foreground mt-3 mb-5">
                  Chat with your data
                </h1>
              </div>

              <div
                className="bg-card dark:bg-card/90 border border-border shadow-lg 
                ring-[1.5px] ring-foreground/10 
                hover:ring-foreground/20 hover:shadow-xl hover:border-foreground/20
                focus-within:ring-primary/30 focus-within:border-primary/50 focus-within:shadow-primary/10
                transition-all duration-200"
              >
                <div className="flex items-center">
                  <div className="flex items-center justify-center h-12 w-12">
                    <ContextPicker
                      selectedContexts={selectedContexts}
                      onSelectContext={handleSelectContext}
                      onRemoveContext={handleRemoveContext}
                      triggerClassName={`flex items-center justify-center h-9 w-9 text-muted-foreground hover:bg-muted hover:text-foreground transition-all duration-200 ${
                        isInputFocused && selectedContexts.length === 0
                          ? "animate-slow-pulse bg-muted/90"
                          : "bg-muted/70"
                      }`}
                      shouldFlash={isInputFocused && selectedContexts.length === 0}
                    />
                  </div>
                  <MentionInput
                    value={inputValue}
                    onChange={setInputValue}
                    onSubmit={handleSendMessage}
                    disabled={isSending}
                    placeholder="Choose a project or dataset & ask questions about your data..."
                    selectedContexts={selectedContexts}
                    onSelectContext={handleSelectContext}
                    onRemoveContext={handleRemoveContext}
                    className="flex-1 dark-input"
                    showSendButton={true}
                    isSending={isSending}
                    hasContext={selectedContexts.length > 0}
                    onFocus={() => setIsInputFocused(true)}
                    onBlur={() => setIsInputFocused(false)}
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
                  <div className="bg-muted p-4 mb-4">
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

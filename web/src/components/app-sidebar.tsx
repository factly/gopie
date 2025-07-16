"use client";

import * as React from "react";
import {
  MessageSquareIcon,
  LifeBuoy,
  Send,
  KeyIcon,
  SettingsIcon,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useParams, usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";

import { NavProjects } from "@/components/nav-projects";
import { NavProjectsChat } from "@/components/nav-projects-chat";
import { NavSecondary } from "@/components/nav-secondary";
import { NavUser } from "@/components/nav-user";
// import { NavSchema } from "@/components/nav-schema";
import { CommandSearch } from "@/components/search/command-search";
import { ThemeToggle } from "@/components/theme/toggle";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  useSidebar,
} from "@/components/ui/sidebar";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const params = useParams();
  const pathname = usePathname();
  const { theme } = useTheme();
  const { state } = useSidebar();

  const [isPeeking, setIsPeeking] = React.useState(false);
  const sidebarRef = React.useRef<HTMLDivElement>(null);
  const timeoutRef = React.useRef<NodeJS.Timeout>(null);

  const projectId = params?.projectId as string;

  React.useEffect(() => {
    // Don't set up peek functionality on home page
    if (pathname === "/") return;

    const handleMouseMove = (e: MouseEvent) => {
      // Only activate peek when sidebar is collapsed
      if (state !== "collapsed") {
        return;
      }

      const isAtLeftEdge = e.clientX <= 10;

      if (isAtLeftEdge && !isPeeking) {
        setIsPeeking(true);
      }
    };

    const handleSidebarMouseEnter = () => {
      // Cancel hiding when mouse enters sidebar
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };

    const handleSidebarMouseLeave = () => {
      // Hide sidebar when mouse leaves and sidebar is collapsed
      if (state === "collapsed" && isPeeking) {
        timeoutRef.current = setTimeout(() => {
          setIsPeeking(false);
        }, 100);
      }
    };

    // Add global mouse move listener
    document.addEventListener("mousemove", handleMouseMove);

    // Add sidebar-specific mouse events
    const sidebarElement = sidebarRef.current;
    if (sidebarElement) {
      sidebarElement.addEventListener("mouseenter", handleSidebarMouseEnter);
      sidebarElement.addEventListener("mouseleave", handleSidebarMouseLeave);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      if (sidebarElement) {
        sidebarElement.removeEventListener(
          "mouseenter",
          handleSidebarMouseEnter
        );
        sidebarElement.removeEventListener(
          "mouseleave",
          handleSidebarMouseLeave
        );
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [state, isPeeking, pathname]);

  // Reset peeking when sidebar state changes to expanded
  React.useEffect(() => {
    if (state === "expanded") {
      setIsPeeking(false);
    }
  }, [state]);

  // Hide sidebar on home page
  if (pathname === "/") {
    return null;
  }

  // Check if we're on a settings page
  const isSettingsPage = pathname.startsWith("/settings");

  const navSecondary = [
    {
      title: "Settings",
      url: "/settings",
      icon: SettingsIcon,
    },
    {
      title: "Support",
      url: "#",
      icon: LifeBuoy,
    },
    {
      title: "Feedback",
      url: "#",
      icon: Send,
    },
  ];

  const shouldShowPeek = state === "collapsed" && isPeeking;

  // Settings navigation items
  const settingsItems = [
    {
      title: "Manage Secrets",
      url: "/settings/secrets",
      icon: KeyIcon,
    },
  ];

  // Settings navigation component
  const NavSettings = () => {
    const isActive = (href: string) => pathname === href;

    return (
      <SidebarGroup>
        <SidebarGroupLabel className="flex items-center gap-2">
          <SettingsIcon className="h-4 w-4" />
          Settings
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {settingsItems.map((item) => (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(item.url)}
                  className="data-[active=true]:bg-sidebar-accent data-[active=true]:text-sidebar-accent-foreground"
                >
                  <Link href={item.url}>
                    <item.icon className="h-4 w-4" />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    );
  };

  return (
    <>
      {/* Peek overlay - shows when collapsed and peeking */}
      <AnimatePresence>
        {shouldShowPeek && (
          <>
            {/* Ghost region - invisible area that covers the gap and prevents flickering */}
            <div
              className="fixed left-0 top-0 bottom-0 w-10 z-30"
              onMouseEnter={() => {
                if (timeoutRef.current) {
                  clearTimeout(timeoutRef.current);
                  timeoutRef.current = null;
                }
              }}
              onMouseLeave={() => {
                if (state === "collapsed" && isPeeking) {
                  timeoutRef.current = setTimeout(() => {
                    setIsPeeking(false);
                  }, 150);
                }
              }}
            />

            {/* Actual floating sidebar */}
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{
                type: "spring",
                damping: 20,
                stiffness: 300,
                mass: 0.8,
                duration: 0.25,
              }}
              className="fixed left-2 top-2 bottom-2 z-40 w-64 bg-sidebar border shadow-2xl overflow-hidden"
              onMouseEnter={() => {
                if (timeoutRef.current) {
                  clearTimeout(timeoutRef.current);
                  timeoutRef.current = null;
                }
              }}
              onMouseLeave={(e) => {
                // Don't close if mouse is moving to a dropdown/popover
                const relatedTarget = e.relatedTarget as HTMLElement;
                if (
                  relatedTarget &&
                  (relatedTarget.closest(
                    "[data-radix-popper-content-wrapper]"
                  ) ||
                    relatedTarget.closest('[role="dialog"]') ||
                    relatedTarget.closest('[role="menu"]') ||
                    relatedTarget.closest('[role="listbox"]') ||
                    relatedTarget.closest(".ghost-region"))
                ) {
                  return;
                }

                if (state === "collapsed" && isPeeking) {
                  timeoutRef.current = setTimeout(() => {
                    // Double-check that no dropdowns are open before closing
                    const openDropdowns = document.querySelectorAll(
                      '[data-state="open"][data-radix-popper-content-wrapper], [data-state="open"][role="dialog"], [data-state="open"][role="menu"], [data-state="open"][role="listbox"]'
                    );
                    if (openDropdowns.length === 0) {
                      setIsPeeking(false);
                    }
                  }, 150);
                }
              }}
            >
              <div className="flex flex-col h-full">
                <SidebarHeader className="border-b">
                  <SidebarMenu>
                    <SidebarMenuItem>
                      <div className="flex items-center justify-between w-full">
                        <SidebarMenuButton
                          size="lg"
                          asChild
                          className="p-0 h-8"
                        >
                          <Link
                            href="/"
                            className="flex items-center justify-center"
                          >
                            <div className="flex items-center justify-center">
                              <Image
                                src={
                                  theme === "dark"
                                    ? "/GoPie_Logo_Dark.svg"
                                    : "/GoPie_Logo.svg"
                                }
                                alt="GoPie"
                                width={80}
                                height={40}
                                className="h-8"
                              />
                            </div>
                          </Link>
                        </SidebarMenuButton>
                        <div className="flex items-center space-x-10">
                          <SidebarMenuButton
                            size="sm"
                            asChild
                            className={
                              pathname === "/chat"
                                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                                : ""
                            }
                          >
                            <Link
                              href="/chat"
                              className="flex items-center justify-center"
                            >
                              <MessageSquareIcon className="h-4 w-4" />
                            </Link>
                          </SidebarMenuButton>
                          <ThemeToggle />
                        </div>
                      </div>
                    </SidebarMenuItem>
                  </SidebarMenu>

                  {!isSettingsPage && (
                    <CommandSearch
                      projectId={projectId}
                      onNavigate={() => {}}
                    />
                  )}
                </SidebarHeader>
                <SidebarContent className="flex-1">
                  {isSettingsPage ? (
                    <NavSettings />
                  ) : (
                    <>
                      <NavProjectsChat />
                      <NavProjects />
                    </>
                  )}
                  <NavSecondary items={navSecondary} className="mt-auto" />
                </SidebarContent>
                <SidebarFooter className="border-t">
                  {/* {!isSettingsPage && (
                    <div className="flex flex-col gap-2 p-2">
                      <NavSchema />
                    </div>
                  )} */}
                  <NavUser />
                </SidebarFooter>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <Sidebar ref={sidebarRef} variant="inset" {...props}>
        <SidebarHeader className="border-b">
          <SidebarMenu>
            <SidebarMenuItem>
              <div className="flex items-center justify-between w-full">
                <SidebarMenuButton size="lg" asChild className="p-0 h-8">
                  <Link href="/" className="flex items-center justify-center">
                    <div className="flex items-center justify-center">
                      <Image
                        src={
                          theme === "dark"
                            ? "/GoPie_Logo_Dark.svg"
                            : "/GoPie_Logo.svg"
                        }
                        alt="GoPie"
                        width={80}
                        height={40}
                        className="h-8"
                      />
                    </div>
                  </Link>
                </SidebarMenuButton>
                <div className="flex items-center space-x-10">
                  <SidebarMenuButton
                    size="sm"
                    asChild
                    className={
                      pathname === "/chat"
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : ""
                    }
                  >
                    <Link
                      href="/chat"
                      className="flex items-center justify-center"
                    >
                      <MessageSquareIcon className="h-4 w-4" />
                    </Link>
                  </SidebarMenuButton>
                  <ThemeToggle />
                </div>
              </div>
            </SidebarMenuItem>
          </SidebarMenu>

          {!isSettingsPage && (
            <CommandSearch projectId={projectId} onNavigate={() => {}} />
          )}
        </SidebarHeader>
        <SidebarContent>
          {isSettingsPage ? (
            <NavSettings />
          ) : (
            <>
              <NavProjectsChat />
              <NavProjects />
            </>
          )}
          <NavSecondary items={navSecondary} className="mt-auto" />
        </SidebarContent>
        <SidebarFooter className="border-t">
          {/* {!isSettingsPage && (
            <div className="flex flex-col gap-2 p-2">
              <NavSchema />
            </div>
          )} */}
          <NavUser />
        </SidebarFooter>
      </Sidebar>
    </>
  );
}

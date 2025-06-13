"use client";

import { SidebarUser } from "@/components/auth/sidebar-user";

export function NavUser() {
  // Use the existing SidebarUser component which already has auth integration
  return <SidebarUser />;
}

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the first available settings page
    router.replace("/settings/secrets");
  }, [router]);

  return null;
}

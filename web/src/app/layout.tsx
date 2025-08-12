import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/components/auth/auth-provider";
import { NavigationProgress } from "@/components/navigation/navigation-progress";
import { ConditionalLayout } from "@/components/conditional-layout";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export function generateMetadata(): Metadata {
  return {
    title: "GoPie",
    description: "Chat with your data using GoPie",
    manifest: "/site.webmanifest",
    icons: {
      icon: "/favicon.svg",
      apple: "/favicon.svg",
    },
    // Removed Sentry.getTraceData() as it may contain non-serializable objects
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-full font-sans`}
      >
        <AuthProvider>
          <Providers>
            <NavigationProgress />
            <ConditionalLayout>
              {children}
            </ConditionalLayout>
            <Toaster />
          </Providers>
        </AuthProvider>
      </body>
    </html>
  );
}

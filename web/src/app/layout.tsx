import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar, Breadcrumb } from "@/components/ui/navbar";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Gopie",
  description: "Gopie",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-full flex flex-col font-sans`}
      >
        <Providers>
          <div className="relative flex min-h-screen flex-col bg-background">
            <Navbar>
              <div className="container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <Breadcrumb />
              </div>
            </Navbar>
            <main className="flex-1 w-full">{children}</main>
          </div>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}

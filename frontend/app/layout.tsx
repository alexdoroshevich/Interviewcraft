import type { Metadata } from "next";
// Geist is available in Next.js 15+ — using Inter (near-identical) until upgrade
import { Inter, JetBrains_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const geist = Inter({ subsets: ["latin"], variable: "--font-sans" });
const geistMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "InterviewCraft — Deliberate Practice for Tech Interviews",
  description:
    "Explainable scoring with evidence, git-diff answer rewriting, rewind micro-practice with delta scoring, and adaptive skill graph memory.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={cn(geist.variable, geistMono.variable)}>
      <head>
        {/* Prevent flash of wrong theme — runs before React hydrates */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme');var p=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';if((t||p)==='dark')document.documentElement.classList.add('dark')})()`,
          }}
        />
      </head>
      <body className="font-sans bg-slate-50 dark:bg-slate-900 transition-colors duration-200">
        <ThemeProvider><TooltipProvider>{children}</TooltipProvider></ThemeProvider>
        <Toaster richColors position="top-right" />
        {process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID && (
          <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
        )}
      </body>
    </html>
  );
}

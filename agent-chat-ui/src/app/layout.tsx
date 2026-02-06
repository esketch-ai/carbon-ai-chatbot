import type { Metadata } from "next";
import "./globals.css";
import React from "react";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "Agent Chat",
  description: "Agent Chat UX by LangChain",
};

// Skip link component for keyboard accessibility
function SkipLink() {
  return (
    <a
      href="#chat-message-input"
      className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-4 focus:left-4 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
    >
      메인 콘텐츠로 건너뛰기
    </a>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <SkipLink />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

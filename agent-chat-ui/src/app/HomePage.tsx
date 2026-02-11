"use client";

import React from "react";
import { Thread } from "@/components/thread";
import { ArtifactProvider } from "@/components/thread/artifact";
import { Toaster } from "@/components/ui/sonner";
import { SettingsProvider } from "@/providers/Settings";
import { StreamProvider } from "@/providers/Stream";
import { ThreadProvider } from "@/providers/Thread";
import { ChatConfig } from "@/lib/config";

interface HomePageProps {
  initialConfig: ChatConfig;
}

export function HomePage({ initialConfig }: HomePageProps) {
  return (
    <div className="w-full h-screen bg-white dark:bg-zinc-900">
      <Toaster />
      <SettingsProvider initialConfig={initialConfig}>
        <ThreadProvider>
          <StreamProvider>
            <ArtifactProvider>
              <Thread />
            </ArtifactProvider>
          </StreamProvider>
        </ThreadProvider>
      </SettingsProvider>
    </div>
  );
}

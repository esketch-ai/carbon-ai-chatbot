import { Suspense } from "react";
import { loadServerConfig } from "@/lib/config-server";
import { HomePage } from "./HomePage";

function LoadingFallback() {
  return (
    <div className="w-full h-screen bg-white dark:bg-zinc-900 flex items-center justify-center">
      <div className="text-gray-500 dark:text-gray-400 text-lg animate-pulse">
        로딩 중...
      </div>
    </div>
  );
}

export default async function DemoPage() {
  const initialConfig = await loadServerConfig();

  return (
    <Suspense fallback={<LoadingFallback />}>
      <HomePage initialConfig={initialConfig} />
    </Suspense>
  );
}

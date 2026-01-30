import { loadServerConfig } from "@/lib/config-server";
import { HomePage } from "./HomePage";

export default async function DemoPage() {
  const initialConfig = await loadServerConfig();

  return <HomePage initialConfig={initialConfig} />;
}

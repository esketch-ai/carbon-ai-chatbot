import { useContext } from "react";
import { SessionContext } from "@/providers/Session";

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionContext.Provider");
  }
  return context;
}

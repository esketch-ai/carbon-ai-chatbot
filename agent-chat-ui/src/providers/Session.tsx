import { createContext } from "react";

export interface SessionContextType {
  resetSessionTimer: () => void;
}

export const SessionContext = createContext<SessionContextType | undefined>(
  undefined,
);

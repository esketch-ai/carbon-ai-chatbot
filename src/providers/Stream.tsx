import React, {
  createContext,
  ReactNode,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { type Message } from "@langchain/langgraph-sdk";
import {
  uiMessageReducer,
  isUIMessage,
  isRemoveUIMessage,
  type UIMessage,
  type RemoveUIMessage,
} from "@langchain/langgraph-sdk/react-ui";
import { useQueryState } from "nuqs";
import { getApiKey } from "@/lib/api-key";
import { useThreads } from "@/hooks/useThreads";
import { toast } from "sonner";
import { AssistantConfigProvider } from "./AssistantConfig";
import { normalizeApiUrl } from "./client";
import { TIMING } from "@/lib/constants";

export type StateType = { messages: Message[]; ui?: UIMessage[] };

const useTypedStream = useStream<
  StateType,
  {
    UpdateType: {
      messages?: Message[] | Message | string;
      ui?: (UIMessage | RemoveUIMessage)[] | UIMessage | RemoveUIMessage;
      context?: Record<string, unknown>;
    };
    CustomEventType: UIMessage | RemoveUIMessage;
  }
>;

export type StreamContextType = ReturnType<typeof useTypedStream>;
const StreamContext = createContext<StreamContextType | undefined>(undefined);

async function sleep(ms: number = TIMING.THREAD_FETCH_DELAY) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function checkGraphStatus(
  apiUrl: string,
  apiKey: string | null,
): Promise<boolean> {
  console.log("[checkGraphStatus] Checking connection to:", apiUrl);
  console.log("[checkGraphStatus] API Key:", apiKey ? `${apiKey.substring(0, 10)}...` : "none");

  if (!apiUrl || apiUrl.trim() === "") {
    console.error("[checkGraphStatus] ❌ API URL is empty");
    return false;
  }

  try {
    const url = `${apiUrl}/info`;
    console.log("[checkGraphStatus] Fetching:", url);

    const res = await fetch(url, {
      ...(apiKey && {
        headers: {
          "X-Api-Key": apiKey,
        },
      }),
    });

    console.log("[checkGraphStatus] Response status:", res.status, res.statusText);
    const isOk = res.ok;
    console.log(`[checkGraphStatus] ${isOk ? "✅" : "❌"} Connection ${isOk ? "successful" : "failed"}`);
    return isOk;
  } catch (e) {
    console.error("[checkGraphStatus] ❌ Error:", e);
    return false;
  }
}

const StreamSession = ({
  children,
  apiKey,
  apiUrl,
  assistantId,
}: {
  children: ReactNode;
  apiKey: string | null;
  apiUrl: string;
  assistantId: string;
}) => {
  const [threadId, setThreadId] = useQueryState("threadId");
  const { getThreads, setThreads } = useThreads();

  // Memoize callbacks to prevent infinite re-renders
  const handleCustomEvent = useCallback(
    (event: unknown, options: { mutate: (fn: (prev: StateType) => StateType) => void }) => {
      if (isUIMessage(event) || isRemoveUIMessage(event)) {
        options.mutate((prev: StateType) => {
          const ui = uiMessageReducer(prev.ui ?? [], event);
          return { ...prev, ui };
        });
      }
    },
    []
  );

  const handleThreadId = useCallback(
    (id: string) => {
      console.log("[StreamSession] New thread ID received:", id);
      setThreadId(id);

      // 즉시 히스토리 갱신 시도
      console.log("[StreamSession] Immediately refetching threads list...");
      getThreads()
        .then((threads) => {
          console.log("[StreamSession] Threads fetched:", threads.length, "threads");
          setThreads(threads);

          // 만약 새 스레드가 아직 안 보이면 짧은 지연 후 다시 시도
          if (!threads.find(t => t.thread_id === id)) {
            console.log("[StreamSession] New thread not found, retrying after 300ms...");
            sleep(300).then(() => {
              getThreads()
                .then(setThreads)
                .catch(console.error);
            });
          }
        })
        .catch((error) => {
          console.error("[StreamSession] Error fetching threads:", error);
        });
    },
    [setThreadId, getThreads, setThreads]
  );

  const streamValue = useTypedStream({
    apiUrl,
    apiKey: apiKey ?? undefined,
    assistantId,
    threadId: threadId ?? null,
    fetchStateHistory: true,
    onCustomEvent: handleCustomEvent,
    onThreadId: handleThreadId,
  });

  // 채팅 기록 로드 확인을 위한 로깅
  useEffect(() => {
    if (threadId) {
      console.log("[StreamSession] Thread ID in URL:", threadId);
      console.log("[StreamSession] Messages count:", streamValue.messages?.length || 0);
      console.log("[StreamSession] Is loading:", streamValue.isLoading);
      console.log("[StreamSession] Messages:", streamValue.messages?.map(m => ({
        type: m.type,
        id: m.id,
        content: typeof m.content === 'string' ? m.content.substring(0, 50) : 'complex'
      })));
    } else {
      console.log("[StreamSession] No thread ID - new conversation");
    }
  }, [threadId, streamValue.messages?.length, streamValue.isLoading, streamValue.messages]);

  useEffect(() => {
    checkGraphStatus(apiUrl, apiKey).then((ok) => {
      if (!ok) {
        toast.error("Failed to connect to LangGraph server", {
          description: () => (
            <p>
              Please ensure your graph is running at <code>{apiUrl}</code> and
              your API key is correctly set (if connecting to a deployed graph).
            </p>
          ),
          duration: 10000,
          richColors: true,
          closeButton: true,
        });
      }
    });
  }, [apiKey, apiUrl]);

  return (
    <StreamContext.Provider value={streamValue}>
      <AssistantConfigProvider
        apiUrl={apiUrl}
        assistantId={assistantId}
        apiKey={apiKey}
      >
        {children}
      </AssistantConfigProvider>
    </StreamContext.Provider>
  );
};

export const StreamProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  // Get environment variables
  const envApiUrl: string | undefined = process.env.NEXT_PUBLIC_API_URL;
  const envAssistantId: string | undefined = process.env.NEXT_PUBLIC_ASSISTANT_ID;
  const envApiKey: string | undefined = process.env.NEXT_PUBLIC_LANGCHAIN_API_KEY;

  // Use URL params with env var fallbacks
  const [apiUrl, _setApiUrl] = useQueryState("apiUrl", {
    defaultValue: envApiUrl || "",
  });
  const [assistantId, _setAssistantId] = useQueryState("assistantId", {
    defaultValue: envAssistantId || "",
  });

  // For API key, use localStorage with env var fallback
  const [apiKey, _setApiKey] = useState(() => {
    const storedKey = getApiKey();
    // If no stored key but env var exists, use and save the env var
    if (!storedKey && envApiKey && typeof window !== "undefined") {
      window.localStorage.setItem("lg:chat:apiKey", envApiKey);
      return envApiKey;
    }
    return storedKey || envApiKey || "";
  });

  const _setApiKeyWrapper = (key: string) => {
    window.localStorage.setItem("lg:chat:apiKey", key);
    _setApiKey(key);
  };

  // Determine final values to use, prioritizing URL params then env vars
  const finalApiUrl = apiUrl || envApiUrl;
  const finalAssistantId = assistantId?.trim() || envAssistantId || "";
  const resolvedApiUrl = useMemo(
    () => normalizeApiUrl(finalApiUrl),
    [finalApiUrl]
  );

  // Log connection parameters
  console.log("[StreamProvider] Connection parameters:", {
    apiUrl,
    envApiUrl,
    finalApiUrl,
    resolvedApiUrl,
    assistantId,
    envAssistantId,
    finalAssistantId,
    apiKey: apiKey ? `${apiKey.substring(0, 10)}...` : "none",
  });

  return (
    <StreamSession
      apiKey={apiKey}
      apiUrl={resolvedApiUrl}
      assistantId={finalAssistantId}
    >
      {children}
    </StreamSession>
  );
};

export default StreamContext;

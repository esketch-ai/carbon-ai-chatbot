import { Thread } from "@langchain/langgraph-sdk";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { PanelRightOpen, PanelRightClose, BookOpen } from "lucide-react";
import { NewChatButton } from "./NewChatButton";
import { ThreadList } from "./ThreadList";
import { ThreadHistoryLoading } from "./ThreadHistoryLoading";
import { ICON_SIZE_SM } from "../constants";

// SettingsDialog는 Radix Dialog의 동적 ID 생성 때문에
// SSR 시점과 클라이언트 시점의 aria-controls 값이 달라질 수 있으므로
// 클라이언트 전용으로 렌더링하여 hydration 경고를 방지한다.
const SettingsDialog = dynamic(
  () =>
    import("@/components/settings/SettingsDialog").then(
      (m) => m.SettingsDialog,
    ),
  {
    ssr: false,
  },
);

interface DesktopSidebarProps {
  threads: Thread[];
  threadsLoading: boolean;
  chatHistoryOpen: boolean;
  onToggleChatHistory: () => void;
  onNewChat: () => void;
  onShowGuide?: () => void;
}

export function DesktopSidebar({
  threads,
  threadsLoading,
  chatHistoryOpen,
  onToggleChatHistory,
  onNewChat,
  onShowGuide,
}: DesktopSidebarProps) {
  return (
    <div className="shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col items-stretch justify-start border-r-[1px] border-border lg:flex">
      {/* Header with collapse button on right */}
      <div className="flex w-full items-center justify-end px-4 pt-1.5">
        <Button
          size="icon"
          className="hover:bg-accent"
          variant="ghost"
          onClick={onToggleChatHistory}
        >
          {chatHistoryOpen ? (
            <PanelRightOpen className="size-5" />
          ) : (
            <PanelRightClose className="size-5" />
          )}
        </Button>
      </div>

      {/* New Chat button */}
      <div className="px-3 mb-2">
        <NewChatButton onClick={onNewChat} />
      </div>

      {/* Guide button */}
      {onShowGuide && (
        <div className="px-3 mb-4">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2 text-sm font-medium hover:bg-accent h-10 cursor-pointer"
            onClick={onShowGuide}
          >
            <BookOpen className={ICON_SIZE_SM} />
            <span>사용 가이드</span>
          </Button>
        </div>
      )}

      {/* Separator */}
      <Separator className="mb-2" />

      {/* Thread list */}
      <div className="flex-1 overflow-hidden">
        {threadsLoading ? (
          <ThreadHistoryLoading />
        ) : (
          <ThreadList threads={threads} />
        )}
      </div>

      <div className="border-t border-border p-4">
        <SettingsDialog />
      </div>
    </div>
  );
}

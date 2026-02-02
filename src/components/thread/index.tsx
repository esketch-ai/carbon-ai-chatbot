import { v4 as uuidv4 } from "uuid";
import { ReactNode, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { UI } from "@/lib/constants";
import { useStreamContext } from "@/hooks/useStreamContext";
import { useState, FormEvent } from "react";
import { Button } from "../ui/button";
import { Checkpoint, Message } from "@langchain/langgraph-sdk";
import { AssistantMessage, AssistantMessageLoading } from "./messages/ai";
import { HumanMessage } from "./messages/human";
import {
  DO_NOT_RENDER_ID_PREFIX,
  ensureToolCallsHaveResponses,
} from "@/lib/ensure-tool-responses";
import {
  ArrowDown,
  LoaderCircle,
  Paperclip,
  Wrench,
  ArrowUp,
  BookOpen,
} from "lucide-react";
import { useQueryState, parseAsBoolean } from "nuqs";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import { toast } from "sonner";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { Label } from "../ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import { useFileUpload } from "@/hooks/use-file-upload";
import { ContentBlocksPreview } from "./ContentBlocksPreview";
import {
  useArtifactContext,
} from "./artifact";
import { useSettings } from "@/hooks/useSettings";
import { FullDescriptionModal } from "./FullDescriptionModal";
import { useAssistantConfig } from "@/hooks/useAssistantConfig";
import { ChatOpeners } from "./ChatOpeners";
import { CategorySelectors } from "./CategorySelectors";

function StickyToBottomContent(props: {
  content: ReactNode;
  footer?: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  const context = useStickToBottomContext();
  return (
    <div
      ref={context.scrollRef}
      style={{ width: "100%", height: "100%" }}
      className={props.className}
    >
      <div
        ref={context.contentRef}
        className={props.contentClassName}
      >
        {props.content}
      </div>

      {props.footer}
    </div>
  );
}

function ScrollToBottom(props: { className?: string }) {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();

  if (isAtBottom) return null;
  return (
    <Button
      variant="outline"
      className={props.className}
      onClick={() => scrollToBottom()}
    >
      <ArrowDown className="h-4 w-4" />
      <span>Scroll to bottom</span>
    </Button>
  );
}

export function Thread() {
  const [artifactContext, setArtifactContext] = useArtifactContext();
  const { config, userSettings, updateUserSettings } = useSettings();

  const [threadId, _setThreadId] = useQueryState("threadId");
  const [hideToolCalls, setHideToolCalls] = useQueryState(
    "hideToolCalls",
    parseAsBoolean.withDefault(false),
  );
  const [input, setInput] = useState("");
  const [fullDescriptionOpen, setFullDescriptionOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const {
    contentBlocks,
    setContentBlocks,
    handleFileUpload,
    dropRef,
    removeBlock,
    resetBlocks: _resetBlocks,
    dragOver,
    handlePaste,
  } = useFileUpload();
  const [firstTokenReceived, setFirstTokenReceived] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");

  const stream = useStreamContext();
  const messages = stream.messages;
  const isLoading = stream.isLoading;
  const {
    assistantId: _activeAssistantId,
  } = useAssistantConfig();

  const lastError = useRef<string | undefined>(undefined);

  const setThreadId = (id: string | null) => {
    _setThreadId(id);
    setArtifactContext({});
  };

  // 기본 ReAct 그래프를 항상 사용 (assistant 선택 불필요)

  useEffect(() => {
    if (!stream.error) {
      lastError.current = undefined;
      return;
    }
    try {
      const message = (stream.error as { message?: string }).message;
      if (!message || lastError.current === message) {
        // Message has already been logged. do not modify ref, return early.
        return;
      }

      // Message is defined, and it has not been logged yet. Save it, and send the error
      lastError.current = message;
      toast.error("An error occurred. Please try again.", {
        description: (
          <p>
            <strong>Error:</strong> <code>{message}</code>
          </p>
        ),
        richColors: true,
        closeButton: true,
      });
    } catch {
      // no-op
    }
  }, [stream.error]);

  // TODO: this should be part of the useStream hook
  const prevMessageLength = useRef(0);
  useEffect(() => {
    if (
      messages.length !== prevMessageLength.current &&
      messages?.length &&
      messages[messages.length - 1].type === "ai"
    ) {
      setFirstTokenReceived(true);
    }

    prevMessageLength.current = messages.length;
  }, [messages]);

  // 스트리밍 완료 감지 - stream.isLoading 또는 메시지 안정화로 감지
  const prevMessageContent = useRef<string>("");
  const streamingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isSubmitting) return;

    // stream.isLoading이 false가 되면 완료
    if (!isLoading && firstTokenReceived) {
      setIsSubmitting(false);
      return;
    }

    // 마지막 AI 메시지의 content 변화 감지
    const lastAiMessage = messages.filter(m => m.type === "ai").pop();
    const currentContent = JSON.stringify(lastAiMessage?.content || "");

    if (currentContent !== prevMessageContent.current) {
      prevMessageContent.current = currentContent;

      // 타이머 리셋
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current);
      }

      // 1.5초 동안 변화 없으면 완료로 간주
      streamingTimeoutRef.current = setTimeout(() => {
        if (isSubmitting && firstTokenReceived) {
          setIsSubmitting(false);
        }
      }, 1500);
    }

    return () => {
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current);
      }
    };
  }, [isSubmitting, isLoading, firstTokenReceived, messages]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (
      (input.trim().length === 0 && contentBlocks.length === 0) ||
      isSubmitting
    )
      return;
    setFirstTokenReceived(false);
    setIsSubmitting(true);

    const newHumanMessage: Message = {
      id: uuidv4(),
      type: "human",
      content: [
        ...(input.trim().length > 0 ? [{ type: "text", text: input }] : []),
        ...contentBlocks,
      ] as Message["content"],
    };

    const toolMessages = ensureToolCallsHaveResponses(stream.messages);

    // 카테고리 정보를 context에 포함
    // Configuration 클래스의 필드만 포함 (category, model, system_prompt, max_search_results)
    const context: Record<string, any> = {};
    if (selectedCategory) {
      context.category = selectedCategory;
    }
    // artifactContext에서 Configuration 필드만 추출 (필요한 경우)
    // 현재는 category만 사용하므로 artifactContext는 제외

    const finalContext =
      Object.keys(context).length > 0 ? context : undefined;

    console.log("[Thread] Submitting message:", {
      threadId: threadId || "new",
      messageCount: stream.messages.length,
      hasContext: !!finalContext,
    });

    stream.submit(
      { messages: [...toolMessages, newHumanMessage], context: finalContext },
      {
        streamMode: ["messages", "values"],  // Hybrid: real-time tokens + node updates
        streamSubgraphs: true,
        streamResumable: true,
        optimisticValues: (prev) => ({
          ...prev,
          context: finalContext,
          messages: [
            ...(prev.messages ?? []),
            ...toolMessages,
            newHumanMessage,
          ],
        }),
      },
    );

    setInput("");
    setContentBlocks([]);
  };

  const handleRegenerate = (
    parentCheckpoint: Checkpoint | null | undefined,
  ) => {
    // Do this so the loading state is correct
    prevMessageLength.current = prevMessageLength.current - 1;
    setFirstTokenReceived(false);
    stream.submit(undefined, {
      checkpoint: parentCheckpoint,
      streamMode: ["messages", "values"],  // Hybrid: real-time tokens + node updates
      streamSubgraphs: true,
      streamResumable: true,
    });
  };

  const chatStarted = !!threadId || !!messages.length;
  const hasNoAIOrToolMessages = !messages.find(
    (m) => m.type === "ai" || m.type === "tool",
  );

  return (
    <div className="flex h-full w-full overflow-hidden">
      <div className="w-full h-full">
        <motion.div
          className={cn(
            "relative flex min-w-0 flex-1 flex-col overflow-hidden h-full",
            !chatStarted && "grid-rows-[1fr]",
          )}
          layout={isLargeScreen}
        >
          {chatStarted && (
            <div className="absolute top-0 left-0 z-10 w-full flex items-center justify-between gap-3 p-4">
              <div className="relative flex items-center justify-start gap-2">
                <motion.button
                  className="flex cursor-pointer items-center gap-2"
                  onClick={() => setThreadId(null)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={config.branding.logoPath}
                    alt="Logo"
                    width={config.branding.logoWidth}
                    height={config.branding.logoHeight}
                  />
                  <span className="text-xl font-semibold tracking-tight">
                    {config.branding.appName}
                  </span>
                </motion.button>
              </div>


              <div className="from-background to-background/0 absolute inset-x-0 top-full h-5 bg-gradient-to-b" />
            </div>
          )}

          <StickToBottom className="relative mt-[68px] flex-1 overflow-hidden">
            <StickyToBottomContent
              className={cn(
                "absolute inset-0 overflow-y-scroll [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-track]:bg-transparent",
                !chatStarted && "mt-0 flex flex-col items-stretch justify-center",
                chatStarted && "grid grid-rows-[1fr_auto]",
                userSettings.chatWidth === "default" ? "px-4" : "px-2",
              )}
              contentClassName={cn(
                messages.length > 0 ? "pt-8 pb-16 mx-auto flex flex-col gap-6 w-full" : "",
                userSettings.chatWidth === "default" ? "max-w-3xl" : "max-w-5xl"
              )}
              content={
                <>
                  {messages
                    .filter((m) => !m.id?.startsWith(DO_NOT_RENDER_ID_PREFIX))
                    .map((message, index) =>
                      message.type === "human" ? (
                        <HumanMessage
                          key={message.id || `${message.type}-${index}`}
                          message={message}
                          isLoading={isLoading}
                        />
                      ) : (
                        <AssistantMessage
                          key={message.id || `${message.type}-${index}`}
                          message={message}
                          isLoading={isLoading}
                          handleRegenerate={handleRegenerate}
                        />
                      ),
                    )}
                  {/* Special rendering case where there are no AI/tool messages, but there is an interrupt.
                    We need to render it outside of the messages list, since there are no messages to render */}
                  {hasNoAIOrToolMessages && !!stream.interrupt && (
                    <AssistantMessage
                      key="interrupt-msg"
                      message={undefined}
                      isLoading={isLoading}
                      handleRegenerate={handleRegenerate}
                    />
                  )}
                  {isLoading && !firstTokenReceived && (
                    <AssistantMessageLoading />
                  )}
                </>
              }
              footer={
                <div className="sticky bottom-0 flex flex-col items-center gap-10 bg-none">
                  {!chatStarted && (
                    <div className={cn(
                      "flex flex-col items-center gap-6 w-full mx-auto",
                      userSettings.chatWidth === "default" ? "max-w-3xl" : "max-w-5xl"
                    )}>
                      <div className="flex flex-col items-center gap-3">
                        <div className="flex items-center gap-3">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={config.branding.logoPath}
                            alt="Logo"
                            width={config.branding.logoWidth * 1.5}
                            height={config.branding.logoHeight * 1.5}
                            className="flex-shrink-0"
                          />
                          <h1 className="text-2xl font-semibold tracking-tight">
                            {config.branding.appName}
                          </h1>
                        </div>
                        {config.branding.description && (
                          <p className="text-muted-foreground text-center text-sm">
                            {config.branding.description}
                          </p>
                        )}
                      </div>
                      {/* 카테고리 선택 UI (우선순위 높음) */}
                      {config.categories && Object.keys(config.categories).length > 0 ? (
                        <CategorySelectors
                          categories={config.categories}
                          disabled={isLoading}
                          onSelectCategory={(categoryName, opener) => {
                            setSelectedCategory(categoryName);
                            setInput(opener);
                            setTimeout(() => {
                              const form = document.querySelector('form');
                              form?.requestSubmit();
                            }, 0);
                          }}
                        />
                      ) : (
                        /* 기존 ChatOpeners (fallback) */
                        config.branding.chatOpeners && config.branding.chatOpeners.length > 0 && (
                          <ChatOpeners
                            disabled={isLoading}
                            chatOpeners={config.branding.chatOpeners}
                            onSelectOpener={(opener) => {
                              setInput(opener);
                              setTimeout(() => {
                                const form = document.querySelector('form');
                                form?.requestSubmit();
                              }, 0);
                            }}
                          />
                        )
                      )}
                    </div>
                  )}

                  <ScrollToBottom className="animate-in fade-in-0 zoom-in-95 absolute bottom-full left-1/2 mb-4 -translate-x-1/2" />

                  <div
                    ref={dropRef}
                    className={cn(
                      "relative z-10 mx-auto mb-8 w-full rounded-3xl shadow-md transition-all border bg-card dark:bg-[#212121]",
                      userSettings.chatWidth === "default" ? "max-w-3xl" : "max-w-5xl",
                      dragOver
                        ? "border-primary border-2 border-dotted"
                        : "border-border",
                    )}
                  >
                    <form
                      onSubmit={handleSubmit}
                      className={cn(
                        "mx-auto grid grid-rows-[1fr_auto]",
                        userSettings.chatWidth === "default" ? "max-w-3xl" : "max-w-5xl"
                      )}
                    >
                      <ContentBlocksPreview
                        blocks={contentBlocks}
                        onRemove={removeBlock}
                      />
                      <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onPaste={handlePaste}
                        onKeyDown={(e) => {
                          if (
                            e.key === "Enter" &&
                            !e.shiftKey &&
                            !e.metaKey &&
                            !e.nativeEvent.isComposing
                          ) {
                            e.preventDefault();
                            // 스트리밍 중일 때 Enter 키 제출 비활성화
                            if (isSubmitting) return;
                            const el = e.target as HTMLElement | undefined;
                            const form = el?.closest("form");
                            form?.requestSubmit();
                          }
                        }}
                        placeholder={config.buttons.chatInputPlaceholder}
                        rows={1}
                        style={{ maxHeight: `${UI.CHAT_TEXTAREA_MAX_HEIGHT}px` }}
                        className="field-sizing-content resize-none border-none bg-transparent px-4 pt-4 pb-2 text-base leading-relaxed shadow-none ring-0 outline-none focus:ring-0 focus:outline-none placeholder:text-muted-foreground overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-track]:bg-transparent"
                      />


                      <div className="flex items-center justify-between gap-2 px-3 pb-3">
                        <div className="flex items-center gap-2">
                          {config.buttons.enableFileUpload && (
                            <>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Label
                                      htmlFor="file-input"
                                      className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg transition-colors hover:bg-accent"
                                    >
                                      <Paperclip className="h-4 w-4 text-muted-foreground" />
                                    </Label>
                                  </TooltipTrigger>
                                  <TooltipContent side="top">
                                    <p>Upload files</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                              <input
                                id="file-input"
                                type="file"
                                onChange={handleFileUpload}
                                multiple
                                accept="image/jpeg,image/png,image/gif,image/webp,application/pdf"
                                className="hidden"
                              />
                            </>
                          )}
                          {/* 도구 호출 표시/숨김 버튼 */}
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  onClick={() => setHideToolCalls((prev) => !prev)}
                                  className={cn(
                                    "flex h-8 w-8 items-center justify-center rounded-lg transition-all",
                                    hideToolCalls
                                      ? "bg-muted text-muted-foreground hover:bg-accent"
                                      : "bg-primary text-primary-foreground hover:bg-primary/90"
                                  )}
                                >
                                  <Wrench className="h-4 w-4" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top">
                                <p>{hideToolCalls ? "Show tool calls" : "Hide tool calls"}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>

                        </div>
                        {isSubmitting ? (
                          <Button
                            key="stop"
                            onClick={() => {
                              stream.stop();
                              setIsSubmitting(false);
                            }}
                            size="icon"
                            variant="outline"
                            className="h-8 w-8"
                          >
                            <LoaderCircle className="h-4 w-4 animate-spin" />
                          </Button>
                        ) : (
                          <Button
                            type="submit"
                            size="icon"
                            className="h-8 w-8 rounded-lg"
                            disabled={
                              isSubmitting ||
                              (!input.trim() && contentBlocks.length === 0)
                            }
                          >
                            <ArrowUp className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </form>
                  </div>
                </div>
              }
            />
          </StickToBottom>
        </motion.div>
      </div>
      <FullDescriptionModal
        open={fullDescriptionOpen}
        onOpenChange={setFullDescriptionOpen}
      />
    </div>
  );
}

import { Thread } from "@langchain/langgraph-sdk";
import { useQueryState } from "nuqs";
import { ThreadListContainer } from "./ThreadListContainer";
import { ThreadItem } from "./thread-item";
import { useThreadOperations } from "../hooks/useThreadOperations";
import { getThreadDisplayText } from "../utils/threadHelpers";

interface ThreadListProps {
  threads: Thread[];
  onThreadClick?: (threadId: string) => void;
}

export function ThreadList({ threads, onThreadClick }: ThreadListProps) {
  const [threadId, setThreadId] = useQueryState("threadId");
  const { deleteThread, updateThreadTitle } = useThreadOperations();

  return (
    <ThreadListContainer>
      <nav
        role="navigation"
        aria-label="대화 히스토리"
      >
        <ul
          role="list"
          aria-label="대화 목록"
          className="flex flex-col"
        >
          {threads.map((t) => {
            const displayText = getThreadDisplayText(t);

            return (
              <li key={t.thread_id} role="listitem">
                <ThreadItem
                  thread={t}
                  isActive={threadId === t.thread_id}
                  displayText={displayText}
                  onSelect={() => {
                    onThreadClick?.(t.thread_id);
                    if (t.thread_id === threadId) return;
                    setThreadId(t.thread_id);
                  }}
                  onDelete={deleteThread}
                  onUpdateTitle={updateThreadTitle}
                />
              </li>
            );
          })}
        </ul>
      </nav>
    </ThreadListContainer>
  );
}

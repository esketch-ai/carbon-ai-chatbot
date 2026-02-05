import { useStreamContext } from "@/hooks/useStreamContext";
import { useThreads } from "@/hooks/useThreads";
import { useSession } from "@/hooks/useSession";
import { useQueryState } from "nuqs";
import { toast } from "sonner";
import { UI_TEXT } from "../constants";
import { logger } from "@/lib/logger";

/**
 * Custom hook for thread CRUD operations
 * Centralizes delete and update logic with error handling
 */
export function useThreadOperations() {
  const { client } = useStreamContext();
  const { getThreads, setThreads } = useThreads();
  const { resetSessionTimer } = useSession();
  const [threadId, setThreadId] = useQueryState("threadId");

  const deleteThread = async (threadIdToDelete: string) => {
    try {
      await client?.threads.delete(threadIdToDelete);
      toast.success(UI_TEXT.deleteSuccess);

      // Refresh threads list
      const updatedThreads = await getThreads();
      setThreads(updatedThreads);

      // If the deleted thread was active, reset the thread
      if (threadId === threadIdToDelete) {
        setThreadId(null);
        resetSessionTimer();
      }
    } catch (error) {
      logger.error("Error deleting thread:", error);
      toast.error(UI_TEXT.deleteError);
    }
  };

  const updateThreadTitle = async (threadIdToUpdate: string, newTitle: string) => {
    try {
      // Update thread metadata with new title
      await client?.threads.update(threadIdToUpdate, {
        metadata: { title: newTitle },
      });
      toast.success(UI_TEXT.updateSuccess);

      // Refresh threads list
      const updatedThreads = await getThreads();
      setThreads(updatedThreads);
    } catch (error) {
      logger.error("Error updating thread title:", error);
      toast.error(UI_TEXT.updateError);
    }
  };

  return {
    deleteThread,
    updateThreadTitle,
  };
}

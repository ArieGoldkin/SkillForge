import { useMutation } from "@tanstack/react-query";

import { mockTutoringAPI } from "@/services/mock.service";
import type { TutoringMessage } from "@/types/api";

interface UseSendMessageProps {
  sessionId: string;
  messages: TutoringMessage[];
  setMessages: React.Dispatch<React.SetStateAction<TutoringMessage[]>>;
}

export function useSendMessage({
  sessionId,
  messages,
  setMessages,
}: UseSendMessageProps) {
  return useMutation({
    mutationFn: (content: string) =>
      mockTutoringAPI.sendMessage(sessionId, content),
    onSuccess: (userMessage) => {
      setMessages([...messages, userMessage]);
      setTimeout(() => {
        const assistantMessage: TutoringMessage = {
          id: "msg-" + Date.now(),
          session_id: sessionId,
          role: "assistant",
          content:
            "That's a great question! Let me help you understand that concept better. What specific aspect would you like to explore?",
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }, 1500);
    },
  });
}

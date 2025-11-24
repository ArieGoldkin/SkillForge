import { useState } from "react";

import { useQuery } from "@tanstack/react-query";

import { mockTutoringAPI } from "@/services/mock.service";
import type { TutoringMessage } from "@/types/api";

export function useTutoringMessages(sessionId: string) {
  const [messages, setMessages] = useState<TutoringMessage[]>([]);

  const { isLoading } = useQuery({
    queryKey: ["tutoring-messages", sessionId],
    queryFn: async () => {
      const msgs = await mockTutoringAPI.getMessages(sessionId);
      setMessages(msgs);
      return msgs;
    },
  });

  return { messages, setMessages, isLoading };
}

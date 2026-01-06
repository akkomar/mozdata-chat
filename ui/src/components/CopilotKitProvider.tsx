'use client';

import { CopilotKit } from "@copilotkit/react-core";
import { useAuth } from "@/components/AuthProvider";
import { useMemo } from "react";

export function CopilotKitProvider({ children }: { children: React.ReactNode }) {
  const { idToken } = useAuth();

  // Memoize headers to avoid recreating on every render
  const headers = useMemo(() => {
    if (idToken) {
      return {
        Authorization: `Bearer ${idToken}`,
      };
    }
    return undefined;
  }, [idToken]);

  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="my_agent"
      headers={headers}
      showDevConsole={false}
    >
      {children}
    </CopilotKit>
  );
}

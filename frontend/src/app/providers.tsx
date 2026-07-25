"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/**
 * Client-side providers. Kept separate so `layout.tsx` stays a Server Component.
 *
 * The QueryClient is created in state (not at module scope) so it is never
 * shared across requests on the server.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // The demo runs on a fixed dataset — refetching mid-pitch would
            // only introduce a chance to fail on stage.
            staleTime: Infinity,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

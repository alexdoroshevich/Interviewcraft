"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { tryRefreshToken } from "@/lib/api";

/**
 * Silently refreshes the access token via the httpOnly refresh cookie.
 * Redirects to /login if the cookie is absent or expired.
 * Returns { ready } — only render the page when ready is true.
 */
export function useAuth() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    tryRefreshToken().then((token) => {
      if (!token) {
        router.push("/login");
      } else {
        setReady(true);
      }
    });
  }, [router]);

  return { ready };
}

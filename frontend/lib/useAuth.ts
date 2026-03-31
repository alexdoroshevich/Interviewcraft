"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Checks for access_token in localStorage.
 * Redirects to /login if missing.
 * Returns { ready } — only render the page when ready is true.
 */
export function useAuth() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  return { ready };
}

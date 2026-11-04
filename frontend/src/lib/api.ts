"use client";

import { useCallback, useEffect, useState } from "react";

export type User = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  is_superadmin: boolean;
  created_at: string | null;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const FALLBACK = "কিছু একটা সমস্যা হয়েছে। আবার চেষ্টা করুন।";

/** JSON fetch against the API with the session cookie. Errors carry the API's message. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`/api/v1${path}`, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init.headers },
    });
  } catch {
    throw new ApiError(0, "সার্ভারের সাথে যোগাযোগ করা যাচ্ছে না। ইন্টারনেট সংযোগ দেখুন।");
  }
  if (!r.ok) {
    let message = FALLBACK;
    try {
      const body = await r.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = "দেওয়া তথ্য সঠিক নয়। ঘরগুলো আবার দেখুন।";
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(r.status, message);
  }
  return r.status === 204 ? (undefined as T) : r.json();
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
}

/** The signed-in user, or null. `loading` is true until the first answer. */
export function useSession() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setUser(await api<User>("/auth/me"));
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    api<User>("/auth/me")
      .then((u) => alive && setUser(u))
      .catch(() => alive && setUser(null))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  return { user, loading, refresh, setUser };
}

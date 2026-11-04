import type { Metadata } from "next";
import { Suspense } from "react";
import { AccountView } from "./account-view";

export const metadata: Metadata = { title: "আমার অ্যাকাউন্ট" };

export default function AccountPage() {
  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-10 sm:py-16">
      <Suspense>
        <AccountView />
      </Suspense>
    </main>
  );
}

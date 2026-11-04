"use client";

import { type InputHTMLAttributes, useState } from "react";

/** Password input with a show/hide eye button. */
export function PasswordInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input {...props} type={show ? "text" : "password"} className={`${className ?? ""} pr-11`} />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "পাসওয়ার্ড লুকান" : "পাসওয়ার্ড দেখুন"}
        aria-pressed={show}
        title={show ? "লুকান" : "দেখুন"}
        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-muted hover:text-accent"
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" strokeLinejoin="round" />
          <circle cx="12" cy="12" r="3" />
          {show && <path d="M4 4l16 16" strokeLinecap="round" />}
        </svg>
      </button>
    </div>
  );
}

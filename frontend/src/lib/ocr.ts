import { ApiError } from "@/lib/api";

export type PassportData = {
  surname: string;
  given_name: string;
  passport_number: string;
  nationality: string;
  issuing_country: string;
  date_of_birth: string | null;
  passport_expiry_date: string | null;
  gender: "male" | "female" | "other" | null;
  checks: Record<string, boolean>;
  valid: boolean;
};

export type Mismatch = { field: string; profile: string | null; passport: string | null };

export const FIELD_LABEL: Record<string, string> = {
  surname: "Surname",
  given_name: "Given name",
  passport_number: "পাসপোর্ট নম্বর",
  date_of_birth: "জন্মতারিখ",
  passport_expiry_date: "মেয়াদ শেষ",
  gender: "লিঙ্গ",
  nationality: "জাতীয়তা",
};

/** POST a file as multipart and return JSON, with the API's error message on failure. */
export async function postFile<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  const r = await fetch(`/api/v1${path}`, { method: "POST", body, credentials: "include" });
  if (!r.ok) {
    const j = await r.json().catch(() => ({}));
    throw new ApiError(r.status, typeof j.detail === "string" ? j.detail : "পড়া যায়নি।");
  }
  return r.json();
}

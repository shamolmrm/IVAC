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
  place_of_birth: "জন্মস্থান",
  marital_status: "বৈবাহিক অবস্থা",
  father_name: "পিতার নাম",
  mother_name: "মাতার নাম",
  spouse_name: "স্বামী/স্ত্রীর নাম",
  passport_issue_date: "ইস্যুর তারিখ",
  passport_issue_place: "ইস্যুর স্থান",
  nid_number: "NID",
  email: "ইমেইল",
  visa_type: "ভিসার ধরন",
  bgd_application_id: "BGD Application ID",
  ivac_mission: "হাইকমিশন",
  expected_journey_date: "যাত্রার তারিখ",
  port_of_arrival: "Port of Arrival",
  port_of_exit: "Port of Exit",
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

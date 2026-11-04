export type Gender = "male" | "female" | "other";
export type MaritalStatus = "single" | "married" | "divorced" | "widowed";
export type VisaType = "tourist" | "medical" | "medical_attendant" | "business" | "student" | "entry" | "other";

export type ApplicantSummary = {
  id: string;
  organization_id: string;
  surname: string;
  given_name: string;
  date_of_birth: string;
  passport_masked: string;
  passport_expiry_date: string;
  visa_type: VisaType;
  assigned_to: string | null;
  created_at: string | null;
};

export type Applicant = {
  id: string;
  organization_id: string;
  surname: string;
  given_name: string;
  gender: Gender;
  date_of_birth: string;
  place_of_birth: string | null;
  nationality: string;
  marital_status: MaritalStatus | null;
  father_name: string | null;
  mother_name: string | null;
  spouse_name: string | null;
  passport_number: string;
  passport_issue_date: string | null;
  passport_expiry_date: string;
  passport_issue_place: string | null;
  nid_number: string | null;
  phone: string | null;
  email: string | null;
  present_address: string | null;
  permanent_address: string | null;
  occupation: string | null;
  visa_type: VisaType;
  notes: string | null;
  bgd_application_id: string | null;
  ivac_mission: string | null;
  expected_journey_date: string | null;
  port_of_arrival: string | null;
  port_of_exit: string | null;
  assigned_to: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type Saved = { applicant: Applicant; warnings: string[] };

export const VISA_LABEL: Record<VisaType, string> = {
  tourist: "ট্যুরিস্ট",
  medical: "মেডিকেল",
  medical_attendant: "মেডিকেল অ্যাটেনডেন্ট",
  business: "বিজনেস",
  student: "স্টুডেন্ট",
  entry: "এন্ট্রি",
  other: "অন্যান্য",
};

export const GENDER_LABEL: Record<Gender, string> = { male: "পুরুষ", female: "নারী", other: "অন্যান্য" };

export const MARITAL_LABEL: Record<MaritalStatus, string> = {
  single: "অবিবাহিত",
  married: "বিবাহিত",
  divorced: "তালাকপ্রাপ্ত",
  widowed: "বিধবা/বিপত্নীক",
};

/** Days until the passport expires (negative = expired). */
export function daysLeft(iso: string): number {
  return Math.floor((new Date(iso).getTime() - Date.now()) / 86_400_000);
}

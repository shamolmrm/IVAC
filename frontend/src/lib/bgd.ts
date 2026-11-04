import type { Applicant } from "@/lib/applicants";

export type BgdData = {
  application_id: string | null;
  registration_date: string | null;
  ivac_mission: string | null;
  surname: string | null;
  given_name: string | null;
  gender: Applicant["gender"] | null;
  date_of_birth: string | null;
  place_of_birth: string | null;
  marital_status: Applicant["marital_status"];
  nid_number: string | null;
  passport_number: string | null;
  passport_issue_date: string | null;
  passport_issue_place: string | null;
  passport_expiry_date: string | null;
  phone: string | null;
  email: string | null;
  present_address: string | null;
  permanent_address: string | null;
  father_name: string | null;
  mother_name: string | null;
  spouse_name: string | null;
  occupation: string | null;
  visa_type: Applicant["visa_type"] | null;
  visa_type_raw: string | null;
  visa_entries: string | null;
  visa_period: string | null;
  expected_journey_date: string | null;
  port_of_arrival: string | null;
  port_of_exit: string | null;
  places_to_visit: string | null;
  missing: string[];
};

/** BGD values -> applicant form prefill (only fields the form has). */
export function bgdToApplicant(b: BgdData): Partial<Applicant> {
  const notes = [
    b.visa_entries && `Entries: ${b.visa_entries}`,
    b.visa_period && `Period: ${b.visa_period}`,
    b.places_to_visit && `Places: ${b.places_to_visit}`,
  ]
    .filter(Boolean)
    .join("\n");
  return {
    surname: b.surname ?? "",
    given_name: b.given_name ?? "",
    gender: b.gender ?? undefined,
    date_of_birth: b.date_of_birth ?? "",
    place_of_birth: b.place_of_birth,
    marital_status: b.marital_status,
    father_name: b.father_name,
    mother_name: b.mother_name,
    spouse_name: b.spouse_name,
    passport_number: b.passport_number ?? "",
    passport_issue_date: b.passport_issue_date,
    passport_issue_place: b.passport_issue_place,
    passport_expiry_date: b.passport_expiry_date ?? "",
    nid_number: b.nid_number,
    phone: b.phone,
    email: b.email,
    present_address: b.present_address,
    permanent_address: b.permanent_address,
    occupation: b.occupation,
    visa_type: b.visa_type ?? undefined,
    notes: notes || null,
    nationality: "BGD",
    bgd_application_id: b.application_id,
    ivac_mission: b.ivac_mission,
    expected_journey_date: b.expected_journey_date,
    port_of_arrival: b.port_of_arrival,
    port_of_exit: b.port_of_exit,
  };
}

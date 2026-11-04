export type OrgRole = "owner" | "manager" | "agent";
export type OrgStatus = "pending" | "active" | "suspended";

export type Org = {
  id: string;
  name: string;
  status: OrgStatus;
  phone: string | null;
  address: string | null;
  trade_license: string | null;
  created_at: string | null;
  my_role: OrgRole | null;
};

export type AdminOrg = Org & { members: number; owner_email: string | null };

export type Member = {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  role: OrgRole;
  is_active: boolean;
  joined_at: string | null;
};

export type Invite = { id: string; email: string; role: OrgRole; created_at: string | null; expires_at: string };

export const ROLE_LABEL: Record<OrgRole, string> = { owner: "Owner", manager: "Manager", agent: "Agent" };

export const STATUS_LABEL: Record<OrgStatus, { text: string; cls: string }> = {
  pending: { text: "অনুমোদনের অপেক্ষায়", cls: "text-amber-600" },
  active: { text: "সক্রিয়", cls: "text-emerald-600" },
  suspended: { text: "স্থগিত", cls: "text-red-600" },
};

export function formatDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString("bn-BD", { dateStyle: "medium" }) : "—";
}

/** Only allow same-site relative redirects (prevents open redirects via ?next=). */
export function safeNext(next: string | null, fallback = "/account"): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Card, PageShell } from "@/components/page-shell";
import { Button, Field, Notice } from "@/components/ui";
import { api, ApiError, post } from "@/lib/api";
import { formatDate, type Invite, type Member, type Org, type OrgRole, ROLE_LABEL, STATUS_LABEL } from "@/lib/orgs";

type Msg = { tone: "success" | "error"; text: string } | null;
const errText = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback);

export function AgencyDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [org, setOrg] = useState<Org | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Org>(`/orgs/${id}`)
      .then(setOrg)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace(`/login?next=/agency/${id}`);
        else setError(errText(err, "লোড করা যায়নি।"));
      });
  }, [id, router]);

  if (error)
    return (
      <PageShell title="এজেন্সি">
        <Notice tone="error">{error}</Notice>
      </PageShell>
    );
  if (!org) return <Notice>লোড হচ্ছে…</Notice>;

  const canManage = org.my_role === "owner" || org.my_role === "manager";
  return (
    <PageShell title={org.name}>
      <Card>
        <dl className="grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-muted">অবস্থা</dt>
          <dd className={STATUS_LABEL[org.status].cls}>{STATUS_LABEL[org.status].text}</dd>
          <dt className="text-muted">আমার ভূমিকা</dt>
          <dd>{org.my_role && ROLE_LABEL[org.my_role]}</dd>
          <dt className="text-muted">ফোন</dt>
          <dd>{org.phone || "—"}</dd>
          <dt className="text-muted">ঠিকানা</dt>
          <dd>{org.address || "—"}</dd>
          <dt className="text-muted">ট্রেড লাইসেন্স</dt>
          <dd>{org.trade_license || "—"}</dd>
        </dl>
        {org.status === "pending" && (
          <p className="mt-4 text-sm text-amber-600">
            এজেন্সিটি অনুমোদনের অপেক্ষায় আছে। অনুমোদনের পর staff আমন্ত্রণ জানাতে পারবেন।
          </p>
        )}
      </Card>
      {canManage && <Staff org={org} />}
    </PageShell>
  );
}

function Staff({ org }: { org: Org }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [msg, setMsg] = useState<Msg>(null);
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isOwner = org.my_role === "owner";

  const load = useCallback(async () => {
    const [m, i] = await Promise.all([
      api<Member[]>(`/orgs/${org.id}/members`),
      api<Invite[]>(`/orgs/${org.id}/invites`),
    ]);
    setMembers(m);
    setInvites(i);
  }, [org.id]);

  useEffect(() => {
    let alive = true;
    Promise.all([api<Member[]>(`/orgs/${org.id}/members`), api<Invite[]>(`/orgs/${org.id}/invites`)])
      .then(([m, i]) => {
        if (!alive) return;
        setMembers(m);
        setInvites(i);
      })
      .catch((err) => alive && setMsg({ tone: "error", text: errText(err, "লোড করা যায়নি।") }));
    return () => {
      alive = false;
    };
  }, [org.id]);

  async function sendInvite(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    setBusy(true);
    setMsg(null);
    setLink(null);
    try {
      const r = await post<Invite & { link: string; emailed: boolean }>(`/orgs/${org.id}/invites`, {
        email: String(form.get("email")).trim(),
        role: String(form.get("role")),
      });
      formEl.reset();
      setLink(r.link);
      setMsg({
        tone: "success",
        text: r.emailed
          ? `${r.email} ঠিকানায় আমন্ত্রণ পাঠানো হয়েছে।`
          : `আমন্ত্রণ তৈরি হয়েছে। নিচের লিংকটি কপি করে ${r.email}-কে পাঠান (৭ দিন বৈধ)।`,
      });
      await load();
    } catch (err) {
      setMsg({ tone: "error", text: errText(err, "আমন্ত্রণ পাঠানো যায়নি।") });
    } finally {
      setBusy(false);
    }
  }

  async function revoke(inviteId: string) {
    try {
      await api(`/orgs/${org.id}/invites/${inviteId}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setMsg({ tone: "error", text: errText(err, "বাতিল করা যায়নি।") });
    }
  }

  async function updateMember(memberId: string, body: { role?: OrgRole; is_active?: boolean }) {
    try {
      await api(`/orgs/${org.id}/members/${memberId}`, { method: "PATCH", body: JSON.stringify(body) });
      await load();
    } catch (err) {
      setMsg({ tone: "error", text: errText(err, "পরিবর্তন করা যায়নি।") });
    }
  }

  const roles: OrgRole[] = isOwner ? ["agent", "manager", "owner"] : ["agent"];

  return (
    <>
      <Card>
        <h2 className="mb-4 font-semibold">Staff</h2>
        {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-muted">
              <tr>
                <th className="py-2 pr-3 font-normal">নাম</th>
                <th className="py-2 pr-3 font-normal">ভূমিকা</th>
                <th className="py-2 pr-3 font-normal">যোগদান</th>
                {isOwner && <th className="py-2 font-normal" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {members.map((m) => (
                <tr key={m.id} className={m.is_active ? "" : "opacity-50"}>
                  <td className="py-2 pr-3">
                    <div>{m.full_name}</div>
                    <div className="break-all text-xs text-muted">{m.email}</div>
                  </td>
                  <td className="py-2 pr-3">
                    {isOwner ? (
                      <select
                        value={m.role}
                        onChange={(e) => updateMember(m.id, { role: e.target.value as OrgRole })}
                        className="rounded border border-line bg-bg px-2 py-1"
                        aria-label={`${m.full_name}-এর ভূমিকা`}
                      >
                        {(["agent", "manager", "owner"] as OrgRole[]).map((r) => (
                          <option key={r} value={r}>
                            {ROLE_LABEL[r]}
                          </option>
                        ))}
                      </select>
                    ) : (
                      ROLE_LABEL[m.role]
                    )}
                  </td>
                  <td className="py-2 pr-3 text-muted">{m.is_active ? formatDate(m.joined_at) : "নিষ্ক্রিয়"}</td>
                  {isOwner && (
                    <td className="py-2 text-right">
                      <button
                        onClick={() => updateMember(m.id, { is_active: !m.is_active })}
                        className="text-xs text-accent"
                      >
                        {m.is_active ? "নিষ্ক্রিয় করুন" : "সক্রিয় করুন"}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h2 className="mb-4 font-semibold">Staff আমন্ত্রণ</h2>
        {org.status !== "active" ? (
          <p className="text-sm text-muted">এজেন্সি অনুমোদিত হলে আমন্ত্রণ পাঠাতে পারবেন।</p>
        ) : (
          <form onSubmit={sendInvite}>
            <Field label="ইমেইল" name="email" type="email" required />
            <label className="mb-4 block">
              <span className="mb-1 block text-sm font-medium">ভূমিকা</span>
              <select name="role" className="w-full rounded-lg border border-line bg-bg px-3 py-2">
                {roles.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABEL[r]}
                  </option>
                ))}
              </select>
            </label>
            <Button type="submit" disabled={busy}>
              {busy ? "অপেক্ষা করুন…" : "আমন্ত্রণ তৈরি করুন"}
            </Button>
          </form>
        )}
        {link && (
          <div className="mt-4 flex gap-2">
            <input readOnly value={link} className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-xs" />
            <button
              onClick={() => navigator.clipboard?.writeText(link)}
              className="shrink-0 rounded-lg border border-line px-3 text-sm hover:border-accent"
            >
              কপি
            </button>
          </div>
        )}
        {invites.length > 0 && (
          <ul className="mt-6 divide-y divide-line text-sm">
            {invites.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="break-all">
                  {i.email} · {ROLE_LABEL[i.role]}
                  <span className="ml-2 text-xs text-muted">মেয়াদ {formatDate(i.expires_at)}</span>
                </span>
                <button onClick={() => revoke(i.id)} className="text-xs text-red-600">
                  বাতিল
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

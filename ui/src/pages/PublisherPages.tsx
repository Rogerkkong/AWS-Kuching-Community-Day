import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { ErrorNote, Spinner, StatusBadge, TierTag } from "../components/Badges";
import { useApp } from "../context";
import { fmtDate, t } from "../i18n";
import type { Doc } from "../types";

interface LogEntry { file?: string; file_name?: string; level: string; message: string; created_at?: string }

const FIELDS: { key: keyof Doc; label: string; options?: string[] }[] = [
  { key: "circular_no", label: "circular_no" },
  { key: "title", label: "title" },
  { key: "issuer", label: "issuer" },
  { key: "doc_type", label: "doc_type", options: ["circular", "policy", "sop", "guideline", "report", "minutes"] },
  { key: "series", label: "series", options: ["PP", "SPP", "SE", "PEKELILING_PERBENDAHARAAN", "STATE", "OTHER"] },
  { key: "jurisdiction", label: "jurisdiction", options: ["FEDERAL", "SARAWAK", "FEDERAL_SARAWAK", "UNKNOWN"] },
  { key: "cluster", label: "cluster" },
  { key: "issue_date", label: "issue_date (YYYY-MM-DD)" },
  { key: "effective_date", label: "effective_date" },
  { key: "expiry_date", label: "expiry_date" },
  { key: "classification_level", label: "classification_level (0 TERBUKA, 1 TERHAD, 2 SULIT)" },
  { key: "one_off", label: "one_off (0/1)" },
  { key: "applicability", label: "applicability" },
  { key: "source_url", label: "source_url" },
];

function MetadataEditor({ doc, onClose, onSaved }: { doc: Doc; onClose: () => void; onSaved: () => void }) {
  const { lang } = useApp();
  const [form, setForm] = useState<Record<string, string>>(() => Object.fromEntries(FIELDS.map((f) => [f.key, doc[f.key] == null ? "" : String(doc[f.key])])));
  const [error, setError] = useState<string | null>(null);
  async function save() {
    const body: Record<string, unknown> = {};
    for (const f of FIELDS) {
      const v = form[f.key as string];
      if (v !== (doc[f.key] == null ? "" : String(doc[f.key]))) body[f.key as string] = f.key === "classification_level" || f.key === "one_off" ? Number(v) : v || null;
    }
    try {
      await api.patch(`/api/publisher/documents/${doc.id}`, body);
      onSaved();
    } catch (e: any) {
      setError(e.message);
    }
  }
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="max-h-[85vh] w-[640px] overflow-auto rounded-xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <span className="font-serif text-lg font-semibold">{doc.circular_no}</span>
          <StatusBadge status={doc.status} issueDate={doc.issue_date} />
        </div>
        <div className="grid grid-cols-[200px_1fr] items-center gap-2 text-[13px]">
          {FIELDS.map((f) => (
            <label key={f.key as string} className="contents">
              <span className="font-mono text-[11px] text-muted">{f.label}</span>
              {f.options ? (
                <select value={form[f.key as string]} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} className="rounded border border-line px-2 py-1">
                  {f.options.map((o) => <option key={o}>{o}</option>)}
                </select>
              ) : (
                <input value={form[f.key as string]} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} className="rounded border border-line px-2 py-1" />
              )}
            </label>
          ))}
        </div>
        {error && <div className="mt-3"><ErrorNote message={error} /></div>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border border-line bg-white px-3 py-1.5 text-[13px]">{t(lang, "cancel")}</button>
          <button onClick={save} className="rounded-md border-0 bg-accent px-4 py-1.5 text-[13px] font-semibold text-white">{t(lang, "save")}</button>
        </div>
      </div>
    </div>
  );
}

export function PubDocsPage() {
  const { lang } = useApp();
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Doc | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const [d, l] = await Promise.all([api.get<{ documents: Doc[] }>("/api/publisher/documents"), api.get<{ log: LogEntry[] }>("/api/publisher/log?limit=60")]);
    setDocs(d.documents);
    setLog(l.log);
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function upload() {
    const files = fileRef.current?.files;
    if (!files?.length) return;
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    setBusy(true);
    setError(null);
    try {
      await api.upload("/api/publisher/upload", form);
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid flex-1 grid-cols-[minmax(0,1fr)_380px] content-start gap-5 overflow-auto px-7 py-6">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 rounded-[10px] border border-dashed border-[#C9C3B7] bg-white px-5 py-4">
          <input ref={fileRef} type="file" accept=".pdf" multiple className="flex-1 text-[13px]" />
          <button onClick={upload} disabled={busy} className="rounded-[7px] border-0 bg-accent px-4 py-2.5 text-[13px] font-semibold text-white">{busy ? t(lang, "uploading") : t(lang, "upload")}</button>
        </div>
        {error && <ErrorNote message={error} />}
        {!docs && <Spinner label={t(lang, "loading")} />}
        {docs && (
          <div className="overflow-hidden rounded-[10px] border border-line bg-white">
            {docs.map((d) => (
              <div key={d.id} className="grid grid-cols-[130px_minmax(0,1fr)_150px_80px_60px] items-center gap-4 border-b border-line-2 px-[18px] py-3 text-[13px]">
                <span className="font-mono text-xs font-semibold">{d.circular_no}</span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="font-medium">{d.title}</span>
                  <span className="text-[11px] text-faint">
                    {t(lang, d.doc_type)} · {t(lang, d.jurisdiction === "UNKNOWN" ? "UNKNOWN_J" : d.jurisdiction)} · {fmtDate(lang, d.issue_date)} · {d.chunk_count} {t(lang, "chunks")}
                    {d.owner_verified ? " · ✓ metadata" : ""}
                  </span>
                  {d.status_reason && d.status !== "IN_FORCE" && d.status !== "RECORD" && <span className="text-xs text-danger">{d.status_reason}</span>}
                </span>
                <StatusBadge status={d.status} issueDate={d.issue_date} />
                <TierTag tier={d.classification_level} />
                <button onClick={() => setEditing(d)} className="border-0 bg-transparent p-0 text-xs font-semibold text-accent">{t(lang, "edit")}</button>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <span className="eyebrow">{t(lang, "ingestLog")}</span>
        <div className="flex max-h-[70vh] flex-col overflow-auto rounded-[10px] bg-navy p-3 font-mono text-[11px] leading-relaxed text-[#C9D4D8]">
          {log.map((l, i) => (
            <div key={i} className={l.level === "error" ? "text-[#F2A59B]" : l.level === "warning" ? "text-[#E9C77B]" : ""}>
              <span className="text-[#6F858E]">{l.file_name ?? l.file}</span> {l.message}
            </div>
          ))}
        </div>
      </div>
      {editing && <MetadataEditor doc={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}

interface Rel {
  id: number;
  source_no: string;
  target_no: string | null;
  target_ref_text: string;
  relation_type: string;
  scope: string | null;
  evidence_text: string | null;
  evidence_page: number | null;
  confidence: number | null;
  verified: number;
  effect: string | null;
  source_jurisdiction: string;
  target_status: string | null;
}

export function PubVerifyPage() {
  const { lang } = useApp();
  const [rels, setRels] = useState<Rel[] | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const load = () => api.get<{ relations: Rel[] }>("/api/publisher/relations").then((r) => setRels(r.relations));
  useEffect(() => {
    load();
  }, []);
  async function act(id: number, action: string, extra: Record<string, unknown> = {}) {
    setBusy(id);
    try {
      await api.post(`/api/publisher/relations/${id}/verify`, { action, ...extra });
      await load();
    } finally {
      setBusy(null);
    }
  }
  if (!rels) return <div className="p-7"><Spinner label={t(lang, "loading")} /></div>;
  return (
    <div className="flex flex-1 flex-col gap-3 overflow-auto px-7 py-6">
      <div className="max-w-[760px] text-[13px] leading-normal text-[#4C5258]">{t(lang, "verifySub")}</div>
      {rels.filter((r) => r.verified === 0).length === 0 && <div className="text-[13px] text-muted">{t(lang, "noPending")}</div>}
      {rels.map((r) => (
        <div key={r.id} className={`grid grid-cols-[minmax(0,1fr)_220px] gap-6 rounded-[10px] border border-line bg-white px-5 py-[18px] ${r.verified !== 0 ? "opacity-70" : ""}`}>
          <div className="flex flex-col gap-2.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-sm font-semibold">{r.source_no}</span>
              <select
                value={r.relation_type}
                disabled={busy === r.id}
                onChange={(e) => act(r.id, "edit", { relation_type: e.target.value })}
                className="rounded border-0 bg-[#EDEAE4] px-2 py-1 font-mono text-[10px] font-semibold tracking-widest text-ink-2"
              >
                {["CANCELS", "SUPERSEDES", "AMENDS", "REFERENCES"].map((x) => <option key={x}>{x}</option>)}
              </select>
              <span className="font-mono text-sm font-semibold">{r.target_no ?? r.target_ref_text}</span>
              {!r.target_no && <span className="text-xs text-danger">{lang === "ms" ? "(tiada dalam korpus)" : "(not in corpus)"}</span>}
              <span className="text-xs text-muted">{t(lang, r.source_jurisdiction)}</span>
            </div>
            {r.evidence_text && <div className="rounded-md bg-[#FAF8F4] px-3 py-2.5 font-serif text-sm leading-relaxed text-[#2B3035]">“{r.evidence_text}”</div>}
            <div className="font-mono text-[11px] text-faint">
              {r.source_no}{r.evidence_page ? ` · p. ${r.evidence_page}` : ""}{r.scope && r.scope !== "whole" ? ` · ${r.scope}` : ""} · {t(lang, "effect")}: {r.effect && r.target_no ? `${r.target_no} → ${t(lang, r.effect)}` : t(lang, "noStatusChange")}
            </div>
          </div>
          <div className="flex flex-col justify-center gap-2">
            <div className="text-xs text-muted">{t(lang, "extractionConfidence")} <span className="font-semibold text-ink">{r.confidence?.toFixed(2) ?? "-"}</span></div>
            {r.verified === 0 ? (
              <>
                <button disabled={busy === r.id} onClick={() => act(r.id, "approve")} className="rounded-[7px] border-0 bg-accent py-2 text-[13px] font-semibold text-white">{t(lang, "approve")}</button>
                <button disabled={busy === r.id} onClick={() => act(r.id, "reject")} className="rounded-[7px] border border-[#D3CEC4] bg-white py-2 text-[13px]">{t(lang, "reject")}</button>
              </>
            ) : (
              <>
                <div className={`text-[13px] font-semibold ${r.verified === 1 ? "text-[#1E6B41]" : "text-danger"}`}>{t(lang, r.verified === 1 ? "verified" : "rejected")}</div>
                <button onClick={() => act(r.id, "reset")} className="border-0 bg-transparent p-0 text-left text-xs text-accent">{t(lang, "undo")}</button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export function PubBuildPage() {
  const { lang } = useApp();
  const [info, setInfo] = useState<any>(null);
  const [version, setVersion] = useState<number>(1);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ packs: any[]; log: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => api.get<any>("/api/publisher/packs").then((r) => { setInfo(r); setVersion(r.next_version); });
  useEffect(() => {
    load();
  }, []);
  async function build() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.post("/api/publisher/build-packs", { version }));
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (!info) return <div className="p-7"><Spinner label={t(lang, "loading")} /></div>;
  const steps = ["Copy documents and verified relations", "Build keyword index (FTS5)", "Build circular-number trigram index", "Write sqlite-vec vectors (1024 dim.)", "Include change summaries and original PDFs", "Compute SHA-256 and Ed25519 signature"];
  return (
    <div className="grid flex-1 grid-cols-[minmax(0,1fr)_420px] content-start gap-5 overflow-auto px-7 py-6">
      <div className="flex flex-col gap-3">
        {info.tiers.map((tr: any) => {
          const latest = info.manifest.packs.filter((p: any) => p.tier === tr.tier).at(-1);
          return (
            <div key={tr.tier} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 rounded-[10px] border border-line bg-white px-5 py-[18px]">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2.5"><span className="text-[15px] font-semibold">Pek {tr.tier === 0 ? "TERBUKA" : tr.tier === 1 ? "TERHAD" : "SULIT"}</span><TierTag tier={tr.tier} /></div>
                <div className="text-[13px] text-[#4C5258]">{tr.documents} {t(lang, "docCount")} · {tr.cancelled} {t(lang, "CANCELLED").toLowerCase()}</div>
                <div className="font-mono text-[11px] text-faint">{tr.tier === 0 ? "Semua peranti pegawai / all officer devices" : "Peranti pegawai bertaraf TERHAD sahaja / cleared devices only"}</div>
              </div>
              <div className="font-mono text-sm font-semibold text-accent">{latest ? `v${latest.version}` : "-"}</div>
            </div>
          );
        })}
        <div className="flex flex-col gap-1.5 rounded-[10px] border border-line bg-white px-5 py-[18px] text-[13px] leading-relaxed text-[#33383D]">
          <span className="eyebrow">Pack</span>
          {info.verified_relations} relations verified · {info.pending_relations} pending · {info.change_summaries} change summaries · embedding model {info.embedding_model} (1024 dim.)
          <span className="font-mono text-[11px] text-faint">{t(lang, "publishedTo")} {info.dist_packs_dir}</span>
        </div>
        {result && (
          <div className="flex flex-col gap-2 rounded-[10px] border border-line bg-white px-5 py-[18px]">
            {result.packs.map((p) => (
              <div key={p.file} className="font-mono text-[11px] leading-relaxed text-ink-2">
                <span className="font-semibold">{p.file}</span> · {p.documents} docs · {p.chunks} chunks · {(p.size_bytes / 1e6).toFixed(1)} MB
                <br />sha256 {p.sha256}
                <br />sig {p.signature.slice(0, 44)}…
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="flex flex-col gap-3.5 rounded-[10px] bg-navy p-5 text-[#E6EBED]">
        <div className="font-serif text-lg font-semibold">{t(lang, "buildAndSign")}</div>
        <div className="flex flex-col">
          {steps.map((s) => (
            <div key={s} className="grid grid-cols-[22px_1fr] gap-2 border-b border-navy-3 py-[7px] text-[13px]">
              <span className={`font-mono text-xs font-semibold ${result ? "text-[#7CC59A]" : busy ? "pulse text-gold" : "text-[#6F858E]"}`}>{result ? "✓" : "·"}</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
        {!info.private_key_present && <ErrorNote message="Private key missing: run scripts/make_keys.py" />}
        {error && <ErrorNote message={error} />}
        <label className="flex items-center gap-3 text-[13px]">
          {t(lang, "version")}
          <input type="number" min={1} value={version} onChange={(e) => setVersion(Number(e.target.value))} className="w-24 rounded border-0 bg-[#0E181D] px-2 py-1 font-mono text-white" />
        </label>
        <button onClick={build} disabled={busy} className="rounded-[7px] border-0 bg-gold py-[11px] text-sm font-semibold text-navy">
          {busy ? t(lang, "loading") : `${t(lang, "buildPacks")} v${version}`}
        </button>
        <div className="rounded-md bg-[#0E181D] p-2.5 font-mono text-[11px] leading-relaxed text-[#A9B7BD]">Ed25519 · {t(lang, "privateKeyNote")}</div>
      </div>
    </div>
  );
}

export function PubAnalyticsPage() {
  const { lang } = useApp();
  const [data, setData] = useState<any>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const ref = useRef<HTMLInputElement>(null);
  const load = () => api.get<any>("/api/publisher/analytics").then(setData);
  useEffect(() => {
    load();
  }, []);
  async function importReport() {
    const f = ref.current?.files?.[0];
    if (!f) return;
    const form = new FormData();
    form.append("file", f);
    const r = await api.upload<{ ok: boolean; message?: string; queries?: number }>("/api/publisher/import-report", form);
    setMsg(r.ok ? `+${r.queries} ${t(lang, "queries")}` : r.message ?? "Error");
    await load();
  }
  if (!data) return <div className="p-7"><Spinner label={t(lang, "loading")} /></div>;
  const Card = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="flex flex-col gap-2 rounded-[10px] border border-line bg-white px-5 py-4">
      <span className="eyebrow">{title}</span>
      {children}
    </div>
  );
  const List = ({ items }: { items: { label: string; value: string | number }[] }) =>
    items.length ? (
      <div className="flex flex-col">
        {items.map((i, k) => (
          <div key={k} className="flex justify-between gap-3 border-b border-line-2 py-1.5 text-[13px]"><span>{i.label}</span><span className="font-mono text-xs text-muted">{i.value}</span></div>
        ))}
      </div>
    ) : (
      <span className="text-[13px] text-faint">{t(lang, "noData")}</span>
    );
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-auto px-7 py-6">
      <div className="flex items-center gap-3 rounded-[10px] border border-dashed border-[#C9C3B7] bg-white px-5 py-3">
        <input ref={ref} type="file" accept=".json" className="flex-1 text-[13px]" />
        <button onClick={importReport} className="rounded-[7px] border-0 bg-accent px-4 py-2 text-[13px] font-semibold text-white">{t(lang, "importReport")}</button>
        {msg && <span className="text-xs text-muted">{msg}</span>}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Card title={t(lang, "reports")}><span className="font-serif text-3xl font-semibold">{data.reports}</span></Card>
        <Card title={t(lang, "queries")}><span className="font-serif text-3xl font-semibold">{data.queries}</span></Card>
        <Card title={t(lang, "unansweredRate")}><span className="font-serif text-3xl font-semibold">{Math.round(data.unanswered_rate * 100)}%</span></Card>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Card title={t(lang, "byCluster")}>
          <List items={data.by_cluster.map((c: any) => ({ label: `${c.cluster} (${c.queries})`, value: `${Math.round(c.rate * 100)}% ${lang === "ms" ? "tidak dijawab" : "unanswered"}` }))} />
        </Card>
        <Card title={t(lang, "topUnanswered")}><List items={data.top_unanswered.map((q: any) => ({ label: q.query, value: q.count }))} /></Card>
        <Card title={t(lang, "topTopics")}><List items={data.top_topics.map((q: any) => ({ label: q.topic, value: q.count }))} /></Card>
        <Card title={t(lang, "excludedOften")}><List items={data.excluded_circulars.map((q: any) => ({ label: q.circular_no, value: q.count }))} /></Card>
        <Card title={t(lang, "lowConfidence")}><List items={data.low_confidence.map((q: string) => ({ label: q, value: "LOW" }))} /></Card>
      </div>
    </div>
  );
}

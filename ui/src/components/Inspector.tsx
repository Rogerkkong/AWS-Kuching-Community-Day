import { useEffect, useState } from "react";
import { api, fetchImage } from "../api";
import { useApp } from "../context";
import { fmtDate, t } from "../i18n";
import { STATUS_STYLE } from "../status";
import type { Doc, Inspect } from "../types";
import { ErrorNote, Spinner, StatusBadge, TierTag } from "./Badges";

interface DocDetail {
  document: Doc;
  page_count: number;
  chunks: { id: number; clause_ref: string; page_start: number; text: string }[];
}

export function DocMeta({ doc }: { doc: Doc }) {
  const { lang } = useApp();
  const rows: [string, string | null][] = [
    [t(lang, "type"), t(lang, doc.doc_type)],
    [t(lang, "jurisdiction"), t(lang, doc.jurisdiction === "UNKNOWN" ? "UNKNOWN_J" : doc.jurisdiction)],
    [t(lang, "date"), fmtDate(lang, doc.issue_date)],
    [t(lang, "effectiveFrom"), doc.effective_date ? fmtDate(lang, doc.effective_date) : null],
    [t(lang, "issuer"), doc.issuer],
    [t(lang, "appliesTo"), doc.applicability],
  ];
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-line bg-white p-3.5">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[13px] font-semibold">{doc.circular_no}</span>
        <span className="flex-1" />
        <StatusBadge status={doc.status} issueDate={doc.issue_date} />
      </div>
      <div className="text-[13px] font-semibold leading-snug">{doc.title}</div>
      {doc.status_reason && doc.status !== "IN_FORCE" && doc.status !== "RECORD" && (
        <div className="text-xs" style={{ color: (STATUS_STYLE[doc.status] ?? STATUS_STYLE.UNKNOWN).fg }}>{doc.status_reason}</div>
      )}
      {doc.status === "UNKNOWN" && <div className="text-xs text-muted">{t(lang, "unknownWarn")}</div>}
      <dl className="grid grid-cols-[110px_1fr] gap-x-3 gap-y-1 text-xs">
        {rows.filter(([, v]) => v).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-faint">{k}</dt>
            <dd className="m-0 text-ink-2">{v}</dd>
          </div>
        ))}
        <dt className="text-faint">{t(lang, "clearance")}</dt>
        <dd className="m-0"><TierTag tier={doc.classification_level} /></dd>
      </dl>
    </div>
  );
}

function PageViewer({ inspect, detail }: { inspect: Inspect; detail: DocDetail }) {
  const { lang } = useApp();
  const [page, setPage] = useState(inspect.page ?? 1);
  const [img, setImg] = useState<{ url: string; highlights: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setPage(inspect.page ?? 1), [inspect.docId, inspect.page, inspect.highlight]);
  useEffect(() => {
    let revoked: string | null = null;
    setImg(null);
    setError(null);
    const q = inspect.highlight ? `?highlight=${encodeURIComponent(inspect.highlight.slice(0, 5000))}` : "";
    fetchImage(`/api/documents/${inspect.docId}/pages/${page}.png${q}`)
      .then((r) => {
        revoked = r.url;
        setImg(r);
      })
      .catch((e) => setError(String(e.message ?? e)));
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [inspect.docId, inspect.highlight, page]);
  const total = detail.page_count || 1;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono text-[13px] font-semibold">{detail.document.circular_no}</span>
        <span className="flex items-center gap-2 text-muted">
          <button className="rounded border border-line bg-white px-2 py-0.5" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</button>
          {t(lang, "page")} {page} {t(lang, "of")} {total} · {t(lang, "originalInPack")}
          <button className="rounded border border-line bg-white px-2 py-0.5" disabled={page >= total} onClick={() => setPage(page + 1)}>›</button>
        </span>
      </div>
      {error && <ErrorNote message={error} />}
      <div className="min-h-[420px] bg-white shadow-[0_1px_3px_rgba(0,0,0,.12),0_8px_24px_rgba(0,0,0,.06)]">
        {img ? <img src={img.url} alt={`${detail.document.circular_no} p.${page}`} className="block w-full" /> : <div className="p-6"><Spinner label={t(lang, "loading")} /></div>}
      </div>
    </div>
  );
}

interface LineageData {
  nodes: Doc[];
  links: { source_doc_id: number; target_doc_id: number; relation_type: string; evidence_text: string | null; evidence_page: number | null; summary_ms: string | null; summary_en: string | null; has_diff: boolean; scope: string | null }[];
}

export function LineageView({ docId, onDiff }: { docId: number; onDiff: (old: number, nw: number) => void }) {
  const { lang, userVersion } = useApp();
  const [data, setData] = useState<LineageData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setData(null);
    api.get<LineageData>(`/api/documents/${docId}/lineage`).then(setData).catch((e) => setError(e.message));
  }, [docId, userVersion]);
  if (error) return <ErrorNote message={error} />;
  if (!data) return <Spinner label={t(lang, "loading")} />;
  if (data.links.length === 0) return <div className="p-6 text-center text-[13px] text-faint">{t(lang, "noLineage")}</div>;
  return (
    <div className="flex flex-col">
      <div className="mb-3 text-xs text-muted">{t(lang, "lineageSub")}</div>
      {data.nodes.map((n) => {
        const incoming = data.links.filter((l) => l.source_doc_id === n.id);
        const st = STATUS_STYLE[n.status] ?? STATUS_STYLE.UNKNOWN;
        const current = n.id === docId;
        return (
          <div key={n.id} className="flex flex-col">
            {incoming.map((l) => {
              const target = data.nodes.find((x) => x.id === l.target_doc_id);
              return (
                <div key={`${l.source_doc_id}-${l.target_doc_id}`} className="grid grid-cols-[20px_1fr] gap-2.5 py-0.5">
                  <div className="flex justify-center"><div className="w-0.5 bg-[#C9C3B7]" /></div>
                  <div className="flex flex-col gap-1.5 pb-3 pt-2.5">
                    <span className="font-mono text-[10px] font-semibold tracking-widest text-muted">
                      {n.circular_no} {t(lang, l.relation_type)} {target?.circular_no}
                      {l.scope && l.scope !== "whole" ? ` · ${l.scope}` : ""}
                    </span>
                    {l.evidence_text && (
                      <span className="font-serif text-xs leading-normal text-ink-2">
                        “{l.evidence_text}” <span className="font-mono text-[11px] text-faint">{n.circular_no}{l.evidence_page ? ` · p. ${l.evidence_page}` : ""}</span>
                      </span>
                    )}
                    {(l.summary_ms || l.summary_en) && (
                      <div className="rounded-md border border-line bg-white px-2.5 py-2 text-xs leading-normal text-[#33383D]">
                        <span className="font-semibold">{t(lang, "whatChanged")} </span>
                        {lang === "ms" ? l.summary_ms : l.summary_en}
                        {l.has_diff && (
                          <button className="ml-2 border-0 bg-transparent p-0 text-xs font-semibold text-accent" onClick={() => onDiff(l.target_doc_id, l.source_doc_id)}>
                            {t(lang, "changesTab")} →
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div className="grid grid-cols-[20px_1fr] items-start gap-2.5">
              <div className="flex justify-center pt-4"><div className="h-3 w-3 rounded-full" style={{ background: st.dot, boxShadow: "0 0 0 3px #EFECE6" }} /></div>
              <div className={`flex flex-col gap-1 rounded-[9px] bg-white px-3.5 py-3 ${current ? "border-2 border-accent" : "border border-line"}`}>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[13px] font-semibold">{n.circular_no}</span>
                  <span className="flex-1 text-xs text-muted">{fmtDate(lang, n.issue_date)}</span>
                  <StatusBadge status={n.status} issueDate={n.issue_date} />
                </div>
                <div className="text-[13px] font-semibold">{n.title}</div>
                {n.status_reason && n.status !== "IN_FORCE" && <div className="text-xs text-[#4C5258]">{n.status_reason}</div>}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface DiffData {
  old: Doc;
  new: Doc;
  summary_ms: string;
  summary_en: string;
  relation_type: string;
  who_is_affected: string | null;
  clauses: { clause_old: string | null; clause_new: string | null; type: string; old_text: string; new_text: string; inline: [string, string][] | null }[];
}

export function DiffView({ oldId, newId }: { oldId: number; newId: number }) {
  const { lang, userVersion } = useApp();
  const [data, setData] = useState<DiffData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setData(null);
    setError(null);
    api.get<DiffData>(`/api/diff?old=${oldId}&new=${newId}`).then(setData).catch((e) => setError(e.message));
  }, [oldId, newId, userVersion]);
  if (error) return <ErrorNote message={error} />;
  if (!data) return <Spinner label={t(lang, "loading")} />;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <span className="font-serif text-[17px] font-semibold">{data.old.circular_no} → {data.new.circular_no}</span>
        <span className="font-mono text-[10px] font-semibold tracking-widest text-muted">{t(lang, data.relation_type)}</span>
      </div>
      <div className="grid gap-2">
        <div className="rounded-lg border border-line bg-white p-3 text-[13px] leading-relaxed">
          <div className="eyebrow mb-1">{t(lang, "changeSummary")} · BM</div>
          {data.summary_ms}
        </div>
        <div className="rounded-lg border border-line bg-white p-3 text-[13px] leading-relaxed">
          <div className="eyebrow mb-1">{t(lang, "changeSummary")} · EN</div>
          {data.summary_en}
        </div>
        {data.who_is_affected && <div className="text-xs text-muted">{t(lang, "whoAffected")}: {data.who_is_affected}</div>}
      </div>
      <div className="grid grid-cols-2 gap-2 text-[11px] font-semibold text-muted">
        <span>{t(lang, "oldVersion")} · {data.old.circular_no}</span>
        <span>{t(lang, "newVersion")} · {data.new.circular_no}</span>
      </div>
      {data.clauses.map((c, i) => (
        <div key={i} className="flex flex-col gap-1.5 rounded-lg border border-line bg-white p-2.5">
          <div className="flex items-center gap-2 font-mono text-[10px] font-semibold tracking-widest">
            <span className={c.type === "ADDED" ? "text-[#1E6B41]" : c.type === "REMOVED" ? "text-[#9A241C]" : "text-[#7A4F00]"}>{t(lang, c.type)}</span>
            <span className="text-muted">{t(lang, "clause")} {c.clause_old ?? "-"} → {c.clause_new ?? "-"}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 font-serif text-xs leading-relaxed">
            <div className="rounded bg-[#FCF3F1] p-2">
              {c.inline ? c.inline.filter(([op]) => op !== "+").map(([op, txt], j) => <span key={j} className={op === "-" ? "bg-[#F4C9C2] line-through" : ""}>{txt} </span>) : c.old_text || "—"}
            </div>
            <div className="rounded bg-[#EEF6F0] p-2">
              {c.inline ? c.inline.filter(([op]) => op !== "-").map(([op, txt], j) => <span key={j} className={op === "+" ? "bg-[#BFE3CB] font-semibold" : ""}>{txt} </span>) : c.new_text || "—"}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Right-hand inspector: page viewer, lineage and what-changed for one document. */
export function Inspector({ inspect, onChange, hideTabs = false }: { inspect: Inspect; onChange: (i: Inspect) => void; hideTabs?: boolean }) {
  const { lang, userVersion } = useApp();
  const [detail, setDetail] = useState<DocDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [diffs, setDiffs] = useState<{ old: number; new: number; label: string }[]>([]);
  useEffect(() => {
    setDetail(null);
    setError(null);
    api.get<DocDetail>(`/api/documents/${inspect.docId}`).then(setDetail).catch((e) => setError(e.message));
    api
      .get<LineageData>(`/api/documents/${inspect.docId}/lineage`)
      .then((l) => {
        const no = (id: number) => l.nodes.find((n) => n.id === id)?.circular_no ?? String(id);
        setDiffs(l.links.filter((x) => x.has_diff).map((x) => ({ old: x.target_doc_id, new: x.source_doc_id, label: `${no(x.target_doc_id)} → ${no(x.source_doc_id)}` })));
      })
      .catch(() => setDiffs([]));
  }, [inspect.docId, userVersion]);
  if (error) return <ErrorNote message={error} />;
  if (!detail) return <Spinner label={t(lang, "loading")} />;
  const diff = inspect.diff ?? diffs[0];
  return (
    <div className="flex flex-col gap-3">
      <DocMeta doc={detail.document} />
      {!hideTabs && <div className="flex gap-1 border-b border-[#DDD8CE]">
        {(["page", "lineage", "changes"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => onChange({ ...inspect, tab, diff: tab === "changes" ? diff : inspect.diff })}
            disabled={tab === "changes" && !diff}
            className={`-mb-px border-0 border-b-2 bg-transparent px-3 py-2 text-[13px] ${inspect.tab === tab ? "border-accent font-semibold text-ink" : "border-transparent text-muted"}`}
          >
            {t(lang, tab === "page" ? "pageTab" : tab === "lineage" ? "lineageTab" : "changesTab")}
          </button>
        ))}
      </div>}
      {inspect.tab === "page" && <PageViewer inspect={inspect} detail={detail} />}
      {inspect.tab === "lineage" && <LineageView docId={inspect.docId} onDiff={(o, n) => onChange({ ...inspect, tab: "changes", diff: { old: o, new: n } })} />}
      {inspect.tab === "changes" && !diff && <div className="p-6 text-center text-[13px] text-faint">{t(lang, "noLineage")}</div>}
      {inspect.tab === "changes" && diff && (
        <>
          {diffs.length > 1 && (
            <div className="flex flex-wrap gap-1.5">
              {diffs.map((d) => (
                <button key={d.label} onClick={() => onChange({ ...inspect, diff: d })} className={`rounded-full border px-2.5 py-1 font-mono text-[11px] ${diff.old === d.old && diff.new === d.new ? "border-accent bg-accent-soft text-accent" : "border-line bg-white"}`}>
                  {d.label}
                </button>
              ))}
            </div>
          )}
          <DiffView oldId={diff.old} newId={diff.new} />
        </>
      )}
    </div>
  );
}

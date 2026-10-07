import { useEffect, useState } from "react";
import { api } from "../api";
import { ErrorNote, Spinner, StatusBadge, TierTag } from "../components/Badges";
import { Inspector } from "../components/Inspector";
import { useApp } from "../context";
import { fmtDate, t } from "../i18n";
import type { Doc, Inspect } from "../types";

const FILTERS = ["all", "IN_FORCE", "AMENDED", "CANCELLED", "RECORD", "UNKNOWN"] as const;

export function LibraryPage() {
  const { lang, userVersion, inspect, openInspect } = useApp();
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [error, setError] = useState<string | null>(null);
  const [local, setLocal] = useState<Inspect | null>(null);

  useEffect(() => {
    setDocs(null);
    setLocal(null);
    api.get<{ documents: Doc[] }>("/api/documents").then((r) => setDocs(r.documents)).catch((e) => setError(e.message));
  }, [userVersion]);

  // Notifications can ask this page to open a document / diff.
  useEffect(() => {
    if (inspect) {
      setLocal(inspect);
      openInspect(null);
    }
  }, [inspect, openInspect]);

  const shown = (docs ?? []).filter((d) => filter === "all" || d.status === filter);
  return (
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_460px]">
      <div className="flex min-h-0 flex-col gap-4 overflow-auto px-7 py-6">
        <div className="flex gap-1.5">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-medium ${filter === f ? "border-navy bg-navy text-white" : "border-[#DAD5CB] bg-white text-ink"}`}
            >
              {f === "all" ? t(lang, "all") : t(lang, f)}
            </button>
          ))}
        </div>
        {error && <ErrorNote message={error} />}
        {!docs && !error && <Spinner label={t(lang, "loading")} />}
        {docs && (
          <div className="overflow-hidden rounded-[10px] border border-line bg-white">
            <div className="grid grid-cols-[112px_minmax(0,1fr)_150px_104px] gap-4 border-b border-line px-[18px] py-[11px] font-mono text-[11px] font-medium uppercase tracking-wider text-faint">
              <span>{t(lang, "number")}</span><span>{t(lang, "title")}</span><span>{t(lang, "status")}</span><span>{t(lang, "date")}</span>
            </div>
            {shown.map((d) => (
              <button
                key={d.id}
                onClick={() => setLocal({ docId: d.id, tab: "page", page: 1 })}
                className={`grid w-full grid-cols-[112px_minmax(0,1fr)_150px_104px] items-center gap-4 border-0 border-b border-line-2 px-[18px] py-[13px] text-left text-[13px] ${local?.docId === d.id ? "bg-accent-soft" : d.status === "CANCELLED" ? "bg-[#FDF8F7]" : "bg-white"} hover:bg-[#FAF8F4]`}
              >
                <span className="font-mono text-xs font-semibold">{d.circular_no}</span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="font-medium">{d.title}</span>
                  {d.status !== "IN_FORCE" && d.status !== "RECORD" && d.status_reason && <span className="text-xs text-danger">{d.status_reason}</span>}
                  <span className="text-[11px] text-faint">
                    {t(lang, d.doc_type)} · {t(lang, d.jurisdiction === "UNKNOWN" ? "UNKNOWN_J" : d.jurisdiction)} · <TierTag tier={d.classification_level} />
                  </span>
                </span>
                <span><StatusBadge status={d.status} issueDate={d.issue_date} /></span>
                <span className="text-[#4C5258]">{fmtDate(lang, d.issue_date)}</span>
              </button>
            ))}
          </div>
        )}
        {docs && <div className="text-xs text-faint">{shown.length} {t(lang, "docCount")}</div>}
      </div>
      <div className="min-h-0 overflow-auto bg-panel p-4">
        {local ? <Inspector inspect={local} onChange={setLocal} /> : <div className="flex h-full items-center justify-center p-10 text-center text-[13px] text-faint">{t(lang, "selectDoc")}</div>}
      </div>
    </div>
  );
}

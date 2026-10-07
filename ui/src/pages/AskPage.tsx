import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, askStream } from "../api";
import { ConfidenceBadge, ErrorNote, StatusBadge } from "../components/Badges";
import { Inspector } from "../components/Inspector";
import { useApp } from "../context";
import { t } from "../i18n";
import type { ActionLine, Excluded, Inspect, Source } from "../types";

type Phase = "idle" | "retrieving" | "generating" | "done" | "error";

interface Final {
  answer: string | null;
  answerable: boolean;
  refusal: boolean;
  citations: string[];
  actions: ActionLine[];
  confidence: string;
  query_log_id: number | null;
  warnings: { code: string; message: string }[];
  sources_ms: number;
  total_ms: number;
  model: string;
}

const SUGGESTIONS = [
  { q: "Berapa hari cuti rehat yang boleh dibawa ke hadapan?", tag: ["Soalan utama", "Hero question"] },
  { q: "Adakah had 10 hari dalam PP 3/2018 masih terpakai?", tag: ["Soalan perangkap", "Trap question"] },
  { q: "Apakah keputusan mesyuarat tentang perancangan cuti akhir tahun?", tag: ["Minit mesyuarat", "Meeting minutes"] },
  { q: "Saya nak mohon cuti tanpa gaji. Apa yang perlu saya buat?", tag: ["Apa perlu saya buat?", "What should I do?"] },
  { q: "What is the work-from-home policy for private contractors?", tag: ["Tiada jawapan", "Unanswerable"] },
];

/** Render text with [S#] chips; only ids present in the sources event become chips. */
function withChips(text: string, valid: Set<number>, onCite: (n: number) => void): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\[S(\d+)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const n = Number(m[1]);
    if (valid.has(n)) {
      out.push(
        <button
          key={`${m.index}-${n}`}
          onClick={() => onCite(n)}
          className="mx-0.5 rounded border border-[#B9C3E3] bg-accent-soft px-[5px] py-px align-[2px] font-mono text-[11px] font-semibold text-accent hover:bg-[#DCE3F5]"
        >
          S{n}
        </button>,
      );
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function AskPage() {
  const { lang, user, packs, userVersion, health } = useApp();
  const [draft, setDraft] = useState("");
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [historical, setHistorical] = useState(false);
  const [sources, setSources] = useState<Source[]>([]);
  const [excluded, setExcluded] = useState<Excluded[]>([]);
  const [comparison, setComparison] = useState<{ mine: string; other: string } | null>(null);
  const [prelimConf, setPrelimConf] = useState<string>("LOW");
  const [warnings, setWarnings] = useState<{ code: string; message: string }[]>([]);
  const [answerText, setAnswerText] = useState("");
  const [actionsText, setActionsText] = useState("");
  const [final, setFinal] = useState<Final | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"sources" | "page" | "lineage" | "changes">("sources");
  const [inspect, setInspect] = useState<Inspect | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // New officer profile: clear the screen so nothing from another clearance stays visible.
    abortRef.current?.abort();
    setPhase("idle");
    setQuestion("");
    setSources([]);
    setExcluded([]);
    setFinal(null);
    setAnswerText("");
    setActionsText("");
    setInspect(null);
    setTab("sources");
  }, [userVersion]);

  const valid = new Set(sources.map((s) => s.n));

  async function ask(q: string) {
    const query = q.trim();
    if (!query) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setQuestion(query);
    setDraft("");
    setPhase("retrieving");
    setSources([]);
    setExcluded([]);
    setComparison(null);
    setWarnings([]);
    setAnswerText("");
    setActionsText("");
    setFinal(null);
    setError(null);
    setFeedback(null);
    setTab("sources");
    let finished = false;
    try {
      await askStream(
        query,
        historical,
        (event, data) => {
          if (event === "sources") {
            setSources(data.sources);
            setExcluded(data.excluded ?? []);
            setComparison(data.comparison ?? null);
            setPrelimConf(data.confidence);
            setWarnings(data.warnings ?? []);
            setPhase("generating");
            if (data.sources.length) setInspect({ docId: data.sources[0].document_id, tab: "page", page: data.sources[0].page, highlight: data.sources[0].text });
          } else if (event === "token") {
            if (data.section === "actions") setActionsText((s) => s + data.text);
            else setAnswerText((s) => s + data.text);
          } else if (event === "final") {
            finished = true;
            setFinal(data);
            setPhase("done");
          } else if (event === "error") {
            finished = true;
            setError(data.message);
            setPhase("error");
          }
        },
        ctrl.signal,
      );
      if (!finished && !ctrl.signal.aborted) {
        setError(t(lang, "streamCut"));
        setPhase("error");
      }
    } catch (e: any) {
      if (e?.name !== "AbortError") {
        setError(`${t(lang, "askFailed")}: ${String(e?.message ?? e)}`);
        setPhase("error");
      }
    }
  }

  function cite(n: number) {
    const s = sources.find((x) => x.n === n);
    if (!s) return;
    setInspect({ docId: s.document_id, tab: "page", page: s.page, highlight: s.text });
    setTab("page");
  }

  function openDoc(docId: number, which: "page" | "lineage" | "changes", page?: number, highlight?: string) {
    setInspect({ docId, tab: which, page, highlight });
    setTab(which);
  }

  async function rate(rating: "up" | "down") {
    if (!final?.query_log_id) return;
    await api.post("/api/feedback", { query_log_id: final.query_log_id, rating });
    setFeedback(rating);
  }

  const statusLine = phase === "retrieving" ? t(lang, "phaseRetrieving") : phase === "generating" ? t(lang, "phaseGenerating") : phase === "done" ? `${t(lang, "phaseDone")} · ${t(lang, "sourcesTime")} ${((final?.sources_ms ?? 0) / 1000).toFixed(1)} s · ${t(lang, "completeTime")} ${((final?.total_ms ?? 0) / 1000).toFixed(1)} s` : "";
  const streamingAnswer = phase === "generating";
  const shownAnswer = final ? final.answer : answerText;
  const actions: ActionLine[] = final ? final.actions : [];
  const mine = comparison ? sources.find((s) => s.id === comparison.mine) : undefined;
  const other = comparison ? sources.find((s) => s.id === comparison.other) : undefined;
  const modelBusy = health?.model.state === "loading";

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_460px]">
      <div className="flex min-h-0 flex-col border-r border-line">
        <div className="flex-1 overflow-auto px-10 py-8">
          <div className="mx-auto flex max-w-[720px] flex-col gap-5">
            {phase === "idle" && (
              <div className="flex flex-col gap-4 pt-14">
                <div className="max-w-[560px] font-serif text-[32px] font-semibold leading-tight tracking-tight">{t(lang, "heroTitle")}</div>
                <div className="max-w-[560px] text-[15px] leading-relaxed text-[#4C5258]">{t(lang, "heroBody")}</div>
                <div className="mt-3 flex flex-col gap-2">
                  <div className="eyebrow">{t(lang, "tryLabel")}</div>
                  {SUGGESTIONS.map((s) => (
                    <button key={s.q} onClick={() => ask(s.q)} className="flex justify-between gap-3 rounded-lg border border-[#E0DBD1] bg-white px-3.5 py-3 text-left text-sm text-ink hover:border-accent">
                      <span>{s.q}</span>
                      <span className="whitespace-nowrap text-xs text-faint">{lang === "ms" ? s.tag[0] : s.tag[1]}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {phase !== "idle" && (
              <>
                <div className="flex flex-col gap-1.5">
                  <div className="eyebrow">{t(lang, "question")}</div>
                  <div className="font-serif text-[22px] font-semibold leading-snug">{question}</div>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted">
                  <span className={`h-[7px] w-[7px] rounded-full ${phase === "done" ? "bg-[#2E8B57]" : phase === "error" ? "bg-[#C0392B]" : "pulse bg-accent"}`} />
                  <span>{statusLine}</span>
                </div>
                {error && <ErrorNote message={error} />}
                {warnings.filter((w) => w.code === "embedding_model_mismatch").map((w) => <ErrorNote key={w.message} message={w.message} />)}

                {excluded.length > 0 && (
                  <div className="flex flex-col gap-2 rounded-lg border border-[#E8CFCB] bg-[#FCF3F1] px-3.5 py-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[13px] font-semibold text-danger">{t(lang, "excludedTitle")}</span>
                      <button onClick={() => openDoc(excluded[0].document_id, "lineage")} className="border-0 bg-transparent p-0 text-xs font-semibold text-accent">{t(lang, "viewLineage")} →</button>
                    </div>
                    {excluded.map((e) => (
                      <div key={e.document_id} className="flex items-baseline gap-2.5 text-[13px]">
                        <span className="font-mono text-xs font-semibold text-ink">{t(lang, "excludedPrefix")}: {e.circular_no}</span>
                        <span className="text-[#5A2A25]">({e.status_reason})</span>
                        <button onClick={() => openDoc(e.document_id, "page", e.page, e.text)} className="ml-auto border-0 bg-transparent p-0 text-xs text-accent">{t(lang, "viewSource")}</button>
                      </div>
                    ))}
                  </div>
                )}

                {(phase === "generating" || phase === "done") && (
                  <div className="flex flex-col gap-3.5 rounded-[10px] border border-line bg-white px-5 py-5">
                    <div className="flex items-center justify-between">
                      <span className="eyebrow">{t(lang, "answer")}</span>
                      <ConfidenceBadge level={final ? final.confidence : prelimConf} />
                    </div>
                    {shownAnswer !== null && (
                      <p className={`m-0 whitespace-pre-line text-base leading-[1.7] ${final?.refusal ? "text-muted" : "text-ink"}`}>
                        {withChips(shownAnswer || "", valid, cite)}
                        {streamingAnswer && <span className="caret" />}
                      </p>
                    )}
                    {streamingAnswer && actionsText && <p className="m-0 whitespace-pre-line text-sm text-muted">{withChips(actionsText, valid, cite)}</p>}
                    {final?.warnings.filter((w) => w.code === "llm_failed" || w.code === "no_packs").map((w) => (
                      <ErrorNote key={w.code} message={`${w.message} ${t(lang, "llmFailedHint")}`} />
                    ))}
                    {sources.some((s) => s.status === "UNKNOWN" && final?.citations.includes(s.id)) && <div className="text-xs text-muted">⚠ {t(lang, "unknownWarn")}</div>}

                    {actions.length > 0 && (
                      <div className="rounded-lg border border-[#C9D3EE] bg-[#F3F6FC] px-4 py-3">
                        <div className="mb-2 text-sm font-semibold text-accent">{t(lang, "whatToDo")}</div>
                        <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
                          {actions.map((a, i) => (
                            <li key={i} className="grid grid-cols-[18px_1fr] text-[14px] leading-normal">
                              <span className="text-accent">✓</span>
                              <span>{a.text} {a.citations.map((n) => withChips(`[S${n}]`, valid, cite))}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {final && (
                      <div className="flex items-center justify-between border-t border-line-2 pt-3 text-xs text-muted">
                        <span className="font-mono">
                          {t(lang, "sourcesTime")} {(final.sources_ms / 1000).toFixed(1)} s · {t(lang, "completeTime")} {(final.total_ms / 1000).toFixed(1)} s · {final.model} · CPU
                        </span>
                        {final.query_log_id && (
                          <div className="flex gap-1.5">
                            {feedback ? (
                              <span>{t(lang, "thanks")}</span>
                            ) : (
                              <>
                                <button onClick={() => rate("up")} className="rounded-md border border-line bg-white px-2.5 py-1 text-xs">👍 {t(lang, "helpful")}</button>
                                <button onClick={() => rate("down")} className="rounded-md border border-line bg-white px-2.5 py-1 text-xs">👎 {t(lang, "notHelpful")}</button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {mine && other && (
                  <div className="flex flex-col gap-2.5">
                    <div className="flex items-baseline justify-between">
                      <span className="text-sm font-semibold">{t(lang, "compareTitle")}</span>
                      <span className="text-xs text-muted">{t(lang, "compareSub")}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2.5">
                      {[mine, other].map((s, i) => (
                        <div key={s.id} className={`flex flex-col gap-1.5 rounded-lg p-3.5 ${i === 0 ? "border border-[#B9C3E3] bg-[#F3F6FC]" : "border border-line bg-white"}`}>
                          <div className="flex justify-between text-xs">
                            <span className="font-semibold">{t(lang, s.jurisdiction)}</span>
                            <span className="text-muted">{i === 0 ? t(lang, "yourRule") : t(lang, "forComparison")}</span>
                          </div>
                          <div className="line-clamp-4 font-serif text-[13px] leading-normal text-[#33383D]">{s.text.split("\n").slice(1).join(" ") || s.text}</div>
                          <button onClick={() => cite(s.n)} className="self-start border-0 bg-transparent p-0 font-mono text-xs font-medium text-accent">
                            {s.circular_no} · {s.clause_ref} [{s.id}]
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div className="flex-none border-t border-line bg-paper px-10 pb-4 pt-3.5">
          <div className="mx-auto flex max-w-[720px] flex-col gap-2.5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                ask(draft);
              }}
              className="flex items-center gap-2 rounded-[10px] border border-[#D3CEC4] bg-white py-1.5 pl-3.5 pr-1.5 focus-within:border-accent"
            >
              <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t(lang, "placeholder")} className="flex-1 border-0 bg-transparent py-2 text-[15px] text-ink outline-none" />
              <button type="submit" disabled={!draft.trim() || phase === "retrieving"} className="rounded-[7px] border-0 bg-accent px-[18px] py-2.5 text-[13px] font-semibold text-white hover:bg-accent-dark">
                {t(lang, "askBtn")}
              </button>
            </form>
            <div className="flex items-center justify-between text-xs text-muted">
              <button onClick={() => setHistorical(!historical)} className="flex items-center gap-2 border-0 bg-transparent p-0 text-xs text-ink-2">
                <span className="relative inline-block h-4 w-7 rounded-full" style={{ background: historical ? "#23408E" : "#C9C3B7" }}>
                  <span className="absolute top-0.5 h-3 w-3 rounded-full bg-white" style={{ left: historical ? 14 : 2 }} />
                </span>
                {t(lang, "includeHistorical")}
              </button>
              <span>
                {modelBusy ? `${t(lang, "modelLoading")} · ` : ""}
                {t(lang, "searching")} {packs.filter((p) => p.tier <= (user?.clearance_level ?? 0)).map((p) => `${p.tier_name} v${p.version}`).join(" + ") || "-"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex min-h-0 flex-col bg-panel">
        <div className="flex flex-none gap-1 border-b border-[#DDD8CE] px-4 pt-3">
          {(["sources", "page", "lineage", "changes"] as const).map((k) => (
            <button
              key={k}
              disabled={k !== "sources" && !inspect}
              onClick={() => {
                setTab(k);
                if (k !== "sources" && inspect) setInspect({ ...inspect, tab: k });
              }}
              className={`-mb-px border-0 border-b-2 bg-transparent px-3 py-2.5 text-[13px] ${tab === k ? "border-accent font-semibold text-ink" : "border-transparent text-muted"}`}
            >
              {t(lang, k === "sources" ? "sourcesTab" : k === "page" ? "pageTab" : k === "lineage" ? "lineageTab" : "changesTab")}
              {k === "sources" && sources.length > 0 && <span className="ml-1.5 font-mono text-[11px] text-faint">{sources.length}</span>}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-auto p-4">
          {tab === "sources" && sources.length === 0 && (
            <div className="flex h-full items-center justify-center p-10 text-center text-[13px] leading-relaxed text-faint">
              {phase === "retrieving" ? t(lang, "phaseRetrieving") : phase === "idle" ? t(lang, "rightEmpty") : t(lang, "refusalNote")}
            </div>
          )}
          {tab === "sources" && sources.length > 0 && (
            <div className="flex flex-col gap-2.5">
              {sources.map((s) => {
                const cited = final?.citations.includes(s.id);
                return (
                  <div key={s.id} className={`flex flex-col gap-2 rounded-[9px] bg-white p-3.5 ${cited ? "border border-[#B9C3E3]" : "border border-line"}`}>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[11px] font-semibold text-accent">{s.id}</span>
                      <span className="font-mono text-[13px] font-semibold">{s.circular_no}</span>
                      <span className="flex-1" />
                      <StatusBadge status={s.status} issueDate={s.issue_date} title={s.status_reason} />
                    </div>
                    <div className="text-[13px] font-semibold leading-snug">{s.title}</div>
                    <div className="font-mono text-[11px] text-muted">
                      {s.breadcrumb} · p. {s.page} · {t(lang, s.jurisdiction === "UNKNOWN" ? "UNKNOWN_J" : s.jurisdiction)}
                      {s.role === "comparison" ? ` · ${t(lang, "forComparison")}` : ""}
                    </div>
                    <div className="line-clamp-5 whitespace-pre-line font-serif text-[13px] leading-normal text-[#33383D]">{s.text}</div>
                    {s.status !== "IN_FORCE" && s.status !== "RECORD" && s.status_reason && <span className="text-[11px] text-danger">{s.status_reason}</span>}
                    <div className="flex gap-3">
                      <button onClick={() => openDoc(s.document_id, "page", s.page, s.text)} className="border-0 bg-transparent p-0 text-xs font-semibold text-accent">{t(lang, "viewSource")} →</button>
                      <button onClick={() => openDoc(s.document_id, "lineage")} className="border-0 bg-transparent p-0 text-xs font-semibold text-accent">{t(lang, "viewLineage")}</button>
                      <button onClick={() => openDoc(s.document_id, "changes")} className="border-0 bg-transparent p-0 text-xs font-semibold text-accent">{t(lang, "whatChanged")}</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {tab !== "sources" && inspect && <Inspector hideTabs inspect={{ ...inspect, tab }} onChange={(i) => { setInspect(i); setTab(i.tab); }} />}
        </div>
      </div>
    </div>
  );
}

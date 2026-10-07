import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { ErrorNote, Spinner } from "../components/Badges";
import { useApp } from "../context";
import { t } from "../i18n";
import { STATUS_STYLE } from "../status";

interface Step { step: string; ok: boolean; detail: string }
interface Result {
  tier: number;
  version: number;
  ok: boolean;
  message?: string;
  steps: Step[];
  previous_version?: number | null;
  changes?: { added: any[]; status_changes: any[]; change_summaries: any[] };
}

export function UpdatesPage() {
  const { lang, packs, refreshPacks, updates, checkUpdates, refreshAlerts, user, go, openInspect } = useApp();
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);
  const [exported, setExported] = useState<string | null>(null);
  const packRef = useRef<HTMLInputElement>(null);
  const sigRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.get<{ update_source: string }>("/api/packs").then((r) => setSource(r.update_source));
  }, []);

  async function saveSource() {
    await api.post("/api/settings", { update_source: source });
  }

  async function check() {
    setBusy("check");
    setError(null);
    setCheckError(null);
    try {
      await saveSource();
      const r = await api.post<{ error?: string }>("/api/packs/check", { source });
      if (r.error) setCheckError(r.error);
      await checkUpdates();
      setCheckedAt(new Date().toLocaleTimeString());
    } finally {
      setBusy(null);
    }
  }

  async function installAll() {
    setBusy("install");
    setError(null);
    try {
      const r = await api.post<{ results: Result[]; error?: string }>("/api/packs/install", { source });
      if (r.error) setError(r.error);
      setResults(r.results);
      await Promise.all([refreshPacks(), refreshAlerts(), checkUpdates()]);
    } finally {
      setBusy(null);
    }
  }

  async function installFile() {
    const pack = packRef.current?.files?.[0];
    const sig = sigRef.current?.files?.[0];
    if (!pack || !sig) return;
    setBusy("file");
    setError(null);
    try {
      const form = new FormData();
      form.append("pack", pack);
      form.append("signature", sig);
      const r = await api.upload<Result & { error_code?: string }>("/api/packs/install-file", form);
      if (!r.ok && !r.steps) setError(r.message ?? t(lang, "installFailed"));
      setResults(r.steps ? [r] : []);
      await Promise.all([refreshPacks(), refreshAlerts()]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  async function rollback(tier: number) {
    await api.post("/api/packs/rollback", { tier });
    await refreshPacks();
  }

  async function exportReport() {
    const r = await api.post<{ path: string }>("/api/analytics/export");
    setExported(r.path);
  }

  const restrictedHidden = (user?.clearance_level ?? 0) < 1 || !packs.some((p) => p.tier === 1);
  // Packs above the officer's clearance are never opened for them, so they are not listed either.
  return (
    <div className="grid flex-1 grid-cols-[minmax(0,1fr)_380px] content-start gap-5 overflow-auto px-7 py-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3.5 rounded-[10px] border border-line bg-white px-[22px] py-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex flex-1 flex-col gap-1.5">
              <span className="eyebrow">{t(lang, "updateChannel")}</span>
              <input value={source} onChange={(e) => setSource(e.target.value)} onBlur={saveSource} className="w-full rounded-md border border-line px-2.5 py-1.5 font-mono text-[12.5px]" />
            </div>
            <div className="flex gap-2 pt-5">
              <button onClick={check} disabled={!!busy} className="rounded-[7px] border border-[#D3CEC4] bg-white px-3.5 py-2.5 text-[13px] font-semibold">
                {busy === "check" ? <Spinner /> : t(lang, "checkUpdates")}
              </button>
              <button onClick={installAll} disabled={!!busy || updates.length === 0} className="rounded-[7px] border-0 bg-accent px-4 py-2.5 text-[13px] font-semibold text-white hover:bg-accent-dark">
                {busy === "install" ? <Spinner /> : `${t(lang, "installUpdates")}${updates.length ? ` (${updates.map((u) => `${u.tier_name} v${u.version}`).join(", ")})` : ""}`}
              </button>
            </div>
          </div>
          {checkError && (
            <ErrorNote
              message={
                /manifest\.json/.test(checkError)
                  ? `${t(lang, "noPacksBuilt")} (${checkError})`
                  : `${t(lang, "sourceUnreachable")} ${checkError}`
              }
            />
          )}
          {!checkError && checkedAt && (
            <div className="text-xs font-semibold text-ink-2">
              {updates.length ? `${t(lang, "foundUpdates")}: ${updates.length}` : t(lang, "noUpdates")} · {checkedAt}
            </div>
          )}
          {!checkError && !checkedAt && updates.length === 0 && <div className="text-xs text-muted">{t(lang, "noUpdates")}</div>}
          {updates.length > 0 && (
            <div className="flex flex-col gap-2">
              <span className="eyebrow">{t(lang, "availableUpdates")}</span>
              {updates.map((u) => {
                const current = packs.find((p) => p.tier === u.tier);
                return (
                  <div key={`${u.tier}-${u.version}`} className="grid grid-cols-[120px_1fr_auto] items-center gap-3 rounded-lg border border-[#EBD9AE] bg-[#FFFBF0] px-3.5 py-2.5 text-[13px]">
                    <span className="font-semibold">Pek {u.tier_name}</span>
                    <span className="text-[#4C5258]">
                      {current ? `v${current.version} → ` : ""}<span className="font-mono font-semibold text-accent">v{u.version}</span> · {u.documents ?? "?"} {t(lang, "docCount")} ·{" "}
                      {((u.size_bytes ?? 0) / 1e6).toFixed(1)} MB · {u.embedding_model}
                      <br />
                      <span className="font-mono text-[11px] text-faint">sha256 {String(u.sha256).slice(0, 16)}… · Ed25519 · {String(u.created_at).slice(0, 16).replace("T", " ")}</span>
                    </span>
                    <span className="text-xs text-[#6A4600]">{current ? t(lang, "newerVersion") : t(lang, "notInstalled")}</span>
                  </div>
                );
              })}
            </div>
          )}
          {error && <ErrorNote message={error} />}
          {results.map((r) => (
            <div key={`${r.tier}-${r.version}`} className="flex flex-col border-t border-line-2">
              <div className="pt-2 font-mono text-xs font-semibold">{r.tier === 0 ? "TERBUKA" : "TERHAD"} v{r.version} {r.ok ? "✓" : "✕"}</div>
              {r.steps.map((s) => (
                <div key={s.step} className="grid grid-cols-[24px_1fr_auto] items-center gap-2.5 border-b border-[#F4F1EC] py-2 text-[13px]">
                  <span className={`font-mono text-[13px] font-semibold ${s.ok ? "text-[#2E8B57]" : "text-[#C0392B]"}`}>{s.ok ? "✓" : "✕"}</span>
                  <span>{t(lang, `step_${s.step}`)}</span>
                  <span className="max-w-[360px] truncate font-mono text-[11px] text-faint" title={s.detail}>{s.detail}</span>
                </div>
              ))}
              {!r.ok && r.message && <div className="pt-2 text-xs text-danger">{r.message}</div>}
            </div>
          ))}
          <div className="text-xs leading-normal text-muted">{t(lang, "tamperNote")}</div>
        </div>

        {results.some((r) => r.ok && r.previous_version && r.changes && (r.changes.added.length || r.changes.status_changes.length)) && (
          <div className="flex flex-col gap-3.5 rounded-[10px] border border-line bg-white px-[22px] py-5">
            <span className="font-serif text-lg font-semibold">{t(lang, "whatChangedUpdate")}</span>
            {results.filter((r) => r.ok && r.previous_version && r.changes).map((r) => (
              <div key={r.tier} className="flex flex-col">
                {r.changes!.added.map((d) => (
                  <div key={`a${d.id}`} className="grid grid-cols-[140px_1fr] gap-4 border-t border-line-2 py-3">
                    <span className="font-mono text-[11px] font-medium uppercase tracking-wider text-[#1E6B41]">{t(lang, "newDoc")}</span>
                    <span className="flex flex-col gap-1"><span className="text-sm font-semibold">{d.circular_no}</span><span className="text-[13px] text-[#4C5258]">{d.title}</span></span>
                  </div>
                ))}
                {r.changes!.status_changes.map((c) => {
                  const summ = r.changes!.change_summaries.find((s) => s.old_doc_id === c.document_id);
                  return (
                    <div key={`s${c.document_id}`} className="grid grid-cols-[140px_1fr] gap-4 border-t border-line-2 py-3">
                      <span className="font-mono text-[11px] font-medium uppercase tracking-wider" style={{ color: (STATUS_STYLE[c.new_status] ?? STATUS_STYLE.UNKNOWN).fg }}>{t(lang, "statusChange")}</span>
                      <span className="flex flex-col gap-1">
                        <span className="text-sm font-semibold">{c.circular_no}: {t(lang, c.old_status)} → {t(lang, c.new_status)}</span>
                        <span className="text-[13px] leading-normal text-[#4C5258]">{c.status_reason}{summ ? ` · ${lang === "ms" ? summ.summary_ms : summ.summary_en}` : ""}</span>
                        {summ && (
                          <button onClick={() => { openInspect({ docId: c.document_id, tab: "changes", diff: { old: summ.old_doc_id, new: summ.new_doc_id } }); go("library"); }} className="self-start border-0 bg-transparent p-0 text-xs font-semibold text-accent">
                            {t(lang, "whatChanged")} →
                          </button>
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-2.5 rounded-[10px] border border-line bg-white px-[22px] py-5">
          <span className="eyebrow">{t(lang, "usageExport")}</span>
          <span className="text-xs text-muted">{t(lang, "usageExportNote")}</span>
          <div className="flex items-center gap-3">
            <button onClick={exportReport} className="rounded-[7px] border border-[#D3CEC4] bg-white px-3.5 py-2 text-[13px] font-semibold">{t(lang, "usageExport")}</button>
            {exported && <span className="font-mono text-[11px] text-muted">{t(lang, "exportedTo")} {exported}</span>}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="eyebrow">{t(lang, "installedPacks")}</div>
        {packs.filter((p) => p.tier <= (user?.clearance_level ?? 0)).map((p) => (
          <div key={p.tier} className="flex flex-col gap-2 rounded-[10px] border border-line bg-white p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">Pek {p.tier_name}</span>
              <span className="font-mono text-xs font-semibold text-accent">v{p.version}</span>
            </div>
            <div className="break-all font-mono text-[11px] leading-relaxed text-muted">
              {p.file_path}
              <br />sha256 {p.sha256.slice(0, 16)}… · {(p.size_bytes / 1e6).toFixed(1)} MB · {p.embedding_model}
            </div>
            {!p.embedding_ok && <ErrorNote message={t(lang, "embeddingMismatch")} />}
            {p.previous_version && (
              <button onClick={() => rollback(p.tier)} className="self-start border-0 bg-transparent p-0 text-xs text-accent">{t(lang, "rollback")} (v{p.previous_version})</button>
            )}
          </div>
        ))}
        {restrictedHidden && <div className="rounded-[10px] border border-dashed border-[#C9C3B7] p-4 text-xs leading-normal text-muted">{t(lang, "lockedPack")}</div>}
        <div className="flex flex-col gap-2 rounded-[10px] border border-line bg-white p-4">
          <span className="text-[13px] font-semibold">{t(lang, "installFromFile")}</span>
          <label className="text-xs text-muted">{t(lang, "packFile")}<input ref={packRef} type="file" accept=".sqlite" className="mt-1 block w-full text-xs" /></label>
          <label className="text-xs text-muted">{t(lang, "sigFile")}<input ref={sigRef} type="file" accept=".json" className="mt-1 block w-full text-xs" /></label>
          <button onClick={installFile} disabled={!!busy} className="self-start rounded-[7px] border border-[#D3CEC4] bg-white px-3 py-1.5 text-xs font-semibold">
            {busy === "file" ? <Spinner /> : t(lang, "install")}
          </button>
        </div>
      </div>
    </div>
  );
}

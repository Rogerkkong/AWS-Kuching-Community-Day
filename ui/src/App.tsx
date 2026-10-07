import { useCallback, useEffect, useMemo, useState } from "react";
import { api, hasToken } from "./api";
import { Spinner } from "./components/Badges";
import { Ctx, type AppCtx, type Page } from "./context";
import { t, type Lang } from "./i18n";
import { AskPage } from "./pages/AskPage";
import { LibraryPage } from "./pages/LibraryPage";
import { PubAnalyticsPage, PubBuildPage, PubDocsPage, PubVerifyPage } from "./pages/PublisherPages";
import { UpdatesPage } from "./pages/UpdatesPage";
import type { Health, Inspect, InstalledPack, Notification, User } from "./types";

const OFFICER_NAV: { page: Page; key: string }[] = [
  { page: "ask", key: "navAsk" },
  { page: "library", key: "navLibrary" },
  { page: "updates", key: "navUpdates" },
];
const PUBLISHER_NAV: { page: Page; key: string }[] = [
  { page: "pub-docs", key: "navPubDocs" },
  { page: "pub-verify", key: "navVerify" },
  { page: "pub-build", key: "navBuild" },
  { page: "pub-analytics", key: "navAnalytics" },
];

function initials(name: string) {
  return name.split(/\s+/).filter((w) => !["bin", "binti", "anak", "a/l", "a/p"].includes(w.toLowerCase())).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

export default function App() {
  const [lang, setLangState] = useState<Lang>("ms");
  const [mode, setMode] = useState<"officer" | "publisher">("officer");
  const [serverMode, setServerMode] = useState<"officer" | "publisher" | "web">("officer");
  const [page, setPage] = useState<Page>("ask");
  const [health, setHealth] = useState<Health | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [packs, setPacks] = useState<InstalledPack[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [updates, setUpdates] = useState<any[]>([]);
  const [inspect, setInspect] = useState<Inspect | null>(null);
  const [userVersion, setUserVersion] = useState(0);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const [dismissModelSetup, setDismissModelSetup] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const [port] = useState(window.location.port);

  const refreshPacks = useCallback(async () => {
    const r = await api.get<{ installed: InstalledPack[] }>("/api/packs");
    setPacks(r.installed);
  }, []);
  const refreshAlerts = useCallback(async () => {
    const r = await api.get<{ notifications: Notification[]; unread: number }>("/api/alerts");
    setNotifications(r.notifications);
    setUnread(r.unread);
  }, []);
  const checkUpdates = useCallback(async () => {
    try {
      const r = await api.post<{ updates: any[] }>("/api/packs/check");
      setUpdates(r.updates ?? []);
    } catch {
      setUpdates([]);
    }
  }, []);
  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api.get<Health>("/health"));
    } catch {
      /* transient */
    }
  }, []);

  const applyView = useCallback(
    async (view: "officer" | "publisher") => {
      setMode(view);
      setPage(view === "publisher" ? "pub-docs" : "ask");
      if (view === "officer") {
        await Promise.all([refreshPacks(), refreshAlerts()]);
        checkUpdates();
      }
    },
    [refreshPacks, refreshAlerts, checkUpdates],
  );

  useEffect(() => {
    if (!hasToken()) return;
    (async () => {
      try {
        const cfg = await api.get<{ mode: "officer" | "publisher"; server_mode: "officer" | "publisher" | "web"; ui_language: Lang }>("/api/config");
        setServerMode(cfg.server_mode ?? cfg.mode);
        setLangState(cfg.ui_language === "en" ? "en" : "ms");
        const u = await api.get<{ users: User[]; current: User }>("/api/users");
        setUsers(u.users);
        setUser(u.current);
        await refreshHealth();
        await applyView(cfg.mode);
      } catch (e: any) {
        setBootError(String(e.message ?? e));
      }
    })();
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, [refreshHealth, applyView]);

  useEffect(() => {
    const id = window.setInterval(refreshHealth, health?.model.state === "ready" ? 15000 : 3000);
    return () => window.clearInterval(id);
  }, [refreshHealth, health?.model.state]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    api.post("/api/settings", { ui_language: l }).catch(() => undefined);
  }, []);

  const switchUser = useCallback(
    async (id: number) => {
      const r = await api.post<{ current: User }>("/api/users/switch", { user_id: id });
      setUser(r.current);
      setInspect(null);
      setUserVersion((v) => v + 1);
      setProfileOpen(false);
      const cfg = await api.get<{ mode: "officer" | "publisher" }>("/api/config");
      await applyView(cfg.mode);
    },
    [applyView],
  );

  const ctx: AppCtx = useMemo(
    () => ({ lang, setLang, mode, page, go: setPage, health, user, users, switchUser, packs, refreshPacks, notifications, unread, refreshAlerts, updates, checkUpdates, inspect, openInspect: setInspect, userVersion }),
    [lang, setLang, mode, page, health, user, users, switchUser, packs, refreshPacks, notifications, unread, refreshAlerts, updates, checkUpdates, inspect, userVersion],
  );

  if (!hasToken()) {
    return (
      <div className="flex h-full items-center justify-center p-10 text-center text-sm text-muted">
        Buka aplikasi melalui pelancar desktop (python -m app.desktop). / Open the app through the desktop launcher.
      </div>
    );
  }
  if (bootError) return <div className="p-10 text-sm text-danger">{bootError}</div>;
  if (!user || !health) return <div className="flex h-full items-center justify-center"><Spinner label="MixUp Navigator..." /></div>;

  const nav = mode === "officer" ? OFFICER_NAV : PUBLISHER_NAV;
  const titles: Record<Page, [string, string]> = {
    ask: ["askTitle", "askSub"],
    library: ["libraryTitle", "librarySub"],
    updates: ["updatesTitle", "updatesSub"],
    "pub-docs": ["navPubDocs", "pubDocsSub"],
    "pub-verify": ["navVerify", "verifySub"],
    "pub-build": ["navBuild", "buildSub"],
    "pub-analytics": ["navAnalytics", "analyticsSub"],
  };
  const needsPacks = mode === "officer" && packs.length === 0;
  const modelMissing = !health.inference.reachable || health.inference.chat_model_present === false || health.inference.embed_model_present === false;
  const modelLine = !health.inference.reachable ? t(lang, "modelError") : health.model.state === "loading" ? t(lang, "modelLoading") : health.model.state === "error" ? t(lang, "modelError") : t(lang, "modelReady");

  return (
    <Ctx.Provider value={ctx}>
      <div className="flex h-full flex-col">
        <div className="flex min-h-0 flex-1">
          <aside className="relative flex w-[236px] flex-none flex-col bg-navy text-[#E6EBED]">
            <div className="flex flex-col gap-0.5 px-5 pb-[18px] pt-[22px]">
              <div className="font-serif text-[19px] font-semibold leading-tight">{t(lang, "appName")}</div>
              <div className="font-mono text-[11px] font-medium uppercase tracking-[.14em] text-[#8FA3AB]">
                {t(lang, "navigator")} · {t(lang, mode === "officer" ? "modeOfficer" : "modePublisher")}
              </div>
            </div>
            <div className="mx-4 mb-[18px] grid grid-cols-2 gap-[3px] rounded-[7px] bg-[#0E181D] p-[3px]">
              {(["ms", "en"] as Lang[]).map((l) => (
                <button key={l} onClick={() => setLang(l)} className={`rounded-[5px] border-0 py-[7px] text-xs font-medium ${lang === l ? "bg-[#E6EBED] text-navy" : "bg-transparent text-[#9AACB3]"}`}>
                  {l === "ms" ? "Bahasa Melayu" : "English"}
                </button>
              ))}
            </div>
            <nav className="flex flex-col gap-0.5 px-2.5">
              {nav.map((n, i) => (
                <button
                  key={n.page}
                  onClick={() => setPage(n.page)}
                  className={`flex items-center gap-3 rounded-md border-0 px-3 py-2.5 text-left text-sm ${page === n.page ? "bg-navy-3 font-semibold text-white" : "bg-transparent text-[#C9D4D8] hover:bg-navy-3"}`}
                >
                  <span className="w-3 font-mono text-[11px] text-[#6F858E]">{i + 1}</span>
                  <span className="flex-1">{t(lang, n.key)}</span>
                  {n.page === "updates" && updates.length > 0 && (
                    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-gold px-1.5 font-mono text-[11px] font-semibold text-navy">{updates.length}</span>
                  )}
                </button>
              ))}
            </nav>
            <div className="flex-1" />
            <div className="mx-4 mb-3 flex flex-col gap-1 rounded-lg bg-navy-2 p-3">
              <div className="flex items-center gap-2 text-[13px] font-semibold"><span className="h-2 w-2 rounded-full bg-[#7CC59A]" />{t(lang, "offlineTitle")}</div>
              <div className="text-xs leading-snug text-[#A9B7BD]">{t(lang, "offlineBody")}</div>
            </div>
            {serverMode !== "publisher" ? (
              <button onClick={() => setProfileOpen(!profileOpen)} className="flex items-center gap-2.5 border-0 border-t border-[#253740] bg-transparent px-4 py-3.5 text-left text-inherit hover:bg-[#1C2B32]">
                <div className="flex h-[34px] w-[34px] flex-none items-center justify-center rounded-full bg-[#E6D3A8] text-xs font-semibold text-navy">{initials(user.name)}</div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-semibold">{user.name}</div>
                  <div className="text-[11px] text-[#9AACB3]">
                    {user.role === "PUBLISHER" ? t(lang, "modePublisher") : t(lang, user.jurisdiction)} · {user.clearance_label} · {user.grade}
                  </div>
                </div>
                <span className="text-[11px] text-[#6F858E]">▲</span>
              </button>
            ) : (
              <div className="border-t border-[#253740] px-4 py-3.5 text-[13px]">{t(lang, "modePublisher")}</div>
            )}
            {profileOpen && (
              <div className="absolute bottom-[70px] left-3 z-20 w-[310px] rounded-[10px] bg-white p-2 text-ink shadow-[0_18px_40px_rgba(0,0,0,.28)]">
                <div className="eyebrow px-2.5 pb-1.5 pt-2">{serverMode === "web" ? t(lang, "switchAccount") : t(lang, "switchOfficer")}</div>
                {users.map((u) => (
                  <button key={u.id} onClick={() => switchUser(u.id)} className={`flex w-full items-center gap-2.5 rounded-lg border-0 px-2.5 py-2 text-left ${u.id === user.id ? "bg-accent-soft" : "bg-white hover:bg-[#FAF8F4]"}`}>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#E6D3A8] text-[11px] font-semibold">{initials(u.name)}</div>
                    <div className="flex-1">
                      <div className="text-[13px] font-semibold">{u.name}</div>
                      <div className="text-[11px] text-muted">
                        {u.role === "PUBLISHER" ? `${t(lang, "modePublisher")} · ` : ""}{t(lang, u.jurisdiction)} · {u.clearance_label} · {u.grade} · {u.scheme}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </aside>

          <main className="relative flex min-w-0 flex-1 flex-col">
            <header className="flex h-16 flex-none items-center justify-between border-b border-line bg-paper px-7">
              <div className="flex flex-col gap-0.5">
                <div className="text-lg font-semibold tracking-tight">{t(lang, titles[page][0])}</div>
                <div className="max-w-[640px] truncate text-xs text-muted">{t(lang, titles[page][1])}</div>
              </div>
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 items-center gap-2 rounded-full border border-[#DAD5CB] bg-white px-3 text-xs" title={t(lang, "offlineBody")}>
                  <span className="h-2 w-2 rounded-full bg-[#2E8B57]" />
                  {t(lang, "offlineTitle")}
                </div>
                {mode === "officer" && (
                  <>
                    <div className="flex h-8 items-center gap-2 rounded-full border border-[#DAD5CB] bg-white px-3 text-xs">
                      <span className="text-faint">{t(lang, "jurisdiction")}</span>
                      <span className="font-semibold">{t(lang, user.jurisdiction)}</span>
                    </div>
                    <button onClick={() => setNotifOpen(!notifOpen)} className="relative flex h-8 items-center gap-2 rounded-full border border-[#DAD5CB] bg-white px-3 text-xs font-medium hover:border-[#9EA3A9]">
                      🔔 {t(lang, "notifications")}
                      {unread > 0 && <span className="flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-[#A3271F] px-1 font-mono text-[10px] font-semibold text-white">{unread}</span>}
                    </button>
                  </>
                )}
              </div>
            </header>

            {notifOpen && (
              <div className="absolute right-7 top-[58px] z-30 w-[420px] overflow-hidden rounded-[10px] border border-line bg-white shadow-[0_18px_44px_rgba(30,28,24,.22)]">
                <div className="flex items-center justify-between border-b border-[#EEEAE3] px-4 py-3.5">
                  <span className="text-sm font-semibold">{t(lang, "notifications")}</span>
                  <button onClick={async () => { await api.post("/api/alerts/read-all"); refreshAlerts(); }} className="border-0 bg-transparent p-0 text-xs text-accent">{t(lang, "markAllRead")}</button>
                </div>
                {notifications.length === 0 && <div className="px-4 py-6 text-center text-[13px] text-faint">{t(lang, "noNotifications")}</div>}
                <div className="max-h-[420px] overflow-auto">
                  {notifications.map((n) => (
                    <button
                      key={n.id}
                      onClick={async () => {
                        await api.post(`/api/alerts/${n.id}/read`);
                        refreshAlerts();
                        setNotifOpen(false);
                        if (n.document_id) {
                          const diff = n.change_type === "STATUS_CHANGE" && n.related_doc_id ? { old: n.document_id, new: n.related_doc_id } : n.change_type === "NEW_DOCUMENT" && n.related_doc_id ? { old: n.related_doc_id, new: n.document_id } : undefined;
                          setInspect({ docId: n.document_id, tab: diff ? "changes" : "lineage", diff });
                          setPage("library");
                        }
                      }}
                      className={`flex w-full flex-col gap-1 border-0 border-b border-[#F0ECE6] px-4 py-3.5 text-left hover:bg-[#FAF8F4] ${n.read ? "bg-white" : "bg-[#FFFBF0]"}`}
                    >
                      <span className={`font-mono text-[11px] font-medium uppercase tracking-wider ${n.change_type === "NEW_DOCUMENT" ? "text-[#1E6B41]" : "text-[#9A241C]"}`}>
                        {t(lang, n.change_type === "NEW_DOCUMENT" ? "newDoc" : "statusChange")} · v{n.pack_version}
                      </span>
                      <span className="text-[13px] font-semibold leading-snug">{n.circular_no}</span>
                      <span className="text-xs leading-snug text-muted">{lang === "ms" ? n.summary_ms : n.summary_en}</span>
                    </button>
                  ))}
                </div>
                <div className="px-4 py-2 text-[11px] text-faint">{t(lang, "notifHint")}</div>
              </div>
            )}

            {mode === "officer" && updates.length > 0 && page !== "updates" && (
              <div className="flex flex-none items-center gap-3.5 border-b border-[#EBD9AE] bg-[#FBF1DA] px-7 py-2.5 text-[13px]">
                <span className="font-semibold text-[#6A4600]">{t(lang, "updateAvailable")}</span>
                <span className="flex-1 text-[#4A4030]">
                  {updates.map((u) => `Pek ${u.tier_name} v${u.version}`).join(" · ")} · {t(lang, "signedByPublisher")}
                </span>
                <button onClick={() => setPage("updates")} className="rounded-md border border-[#C9A85E] bg-white px-3 py-1.5 text-xs font-semibold text-[#4A3500]">{t(lang, "viewUpdate")}</button>
              </div>
            )}

            {modelMissing && !dismissModelSetup && !needsPacks && (
              <div className="flex flex-none items-start gap-4 border-b border-[#E8CFCB] bg-[#FCF3F1] px-7 py-3 text-[13px]">
                <div className="flex-1">
                  <div className="font-semibold text-danger">{t(lang, "setupTitle")}</div>
                  <div className="text-[#5A2A25]">{t(lang, "setupNoModel")}</div>
                  <div className="mt-1 font-mono text-[11px] text-ink-2">{t(lang, "setupOllama")} ollama pull qwen3:4b · ollama pull bge-m3 {health.inference.detail ? `· ${health.inference.detail}` : ""}</div>
                </div>
                <button onClick={() => setDismissModelSetup(true)} className="rounded-md border border-line bg-white px-3 py-1.5 text-xs">{t(lang, "continueAnyway")}</button>
              </div>
            )}

            {needsPacks && page !== "updates" ? (
              <div className="flex flex-1 items-center justify-center p-10">
                <div className="flex max-w-[560px] flex-col gap-4 rounded-xl border border-line bg-white p-8">
                  <div className="font-serif text-2xl font-semibold">{t(lang, "setupTitle")}</div>
                  <div className="text-sm text-[#4C5258]">{t(lang, "setupNoPacks")}</div>
                  {modelMissing && <div className="text-sm text-[#4C5258]">{t(lang, "setupNoModel")}<div className="mt-1 font-mono text-xs">ollama pull qwen3:4b · ollama pull bge-m3</div></div>}
                  <div className="flex gap-2">
                    <button onClick={async () => { await checkUpdates(); setPage("updates"); }} className="rounded-[7px] border-0 bg-accent px-4 py-2.5 text-[13px] font-semibold text-white">{t(lang, "checkUpdates")}</button>
                    <button onClick={() => setPage("updates")} className="rounded-[7px] border border-[#D3CEC4] bg-white px-4 py-2.5 text-[13px] font-semibold">{t(lang, "installFromFile")}</button>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {page === "ask" && <AskPage />}
                {page === "library" && <LibraryPage />}
                {page === "updates" && <UpdatesPage />}
                {page === "pub-docs" && <PubDocsPage />}
                {page === "pub-verify" && <PubVerifyPage />}
                {page === "pub-build" && <PubBuildPage />}
                {page === "pub-analytics" && <PubAnalyticsPage />}
              </>
            )}
          </main>
        </div>

        <div className="flex h-[26px] flex-none items-center gap-5 border-t border-[#D6D1C7] bg-chrome px-3.5 font-mono text-[11px] text-[#4C5258]">
          <span className="flex items-center gap-1.5"><span className={`h-1.5 w-1.5 rounded-full ${online ? "bg-[#C98A0B]" : "bg-[#2E8B57]"}`} />{t(lang, online ? "networkOn" : "networkOff")}</span>
          <span className="flex items-center gap-1.5">
            {health.model.state === "loading" && <span className="pulse h-1.5 w-1.5 rounded-full bg-accent" />}
            Model {health.inference.backend === "fake" ? "fake-extractive" : health.inference.chat_model} · {modelLine}
          </span>
          {mode === "officer" && <span>{packs.filter((p) => p.tier <= user.clearance_level).map((p) => `${p.tier_name} v${p.version}`).join(" · ") || "-"}</span>}
          <span className="flex-1" />
          <span>API 127.0.0.1:{port} · {t(lang, "apiLine")}</span>
        </div>
      </div>
    </Ctx.Provider>
  );
}

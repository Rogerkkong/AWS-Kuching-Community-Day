import { createContext, useContext } from "react";
import type { Lang } from "./i18n";
import type { Health, Inspect, InstalledPack, Notification, User } from "./types";

export type Page = "ask" | "library" | "updates" | "pub-docs" | "pub-verify" | "pub-build" | "pub-analytics";

export interface AppCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  mode: "officer" | "publisher";
  page: Page;
  go: (p: Page) => void;
  health: Health | null;
  user: User | null;
  users: User[];
  switchUser: (id: number) => Promise<void>;
  packs: InstalledPack[];
  refreshPacks: () => Promise<void>;
  notifications: Notification[];
  unread: number;
  refreshAlerts: () => Promise<void>;
  updates: any[];
  checkUpdates: () => Promise<void>;
  inspect: Inspect | null;
  openInspect: (i: Inspect | null) => void;
  userVersion: number; // bumps when the user changes so pages refetch
}

export const Ctx = createContext<AppCtx>(null as unknown as AppCtx);
export const useApp = () => useContext(Ctx);

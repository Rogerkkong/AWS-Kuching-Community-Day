import { fmtDate, t, type Lang } from "./i18n";

// Status is always shown as text + colour (never colour alone).
export const STATUS_STYLE: Record<string, { fg: string; bg: string; dot: string }> = {
  IN_FORCE: { fg: "#1E6B41", bg: "#E2F0E7", dot: "#2E8B57" },
  AMENDED: { fg: "#7A4F00", bg: "#FAEDD0", dot: "#C98A0B" },
  CANCELLED: { fg: "#9A241C", bg: "#F7E0DC", dot: "#C0392B" },
  UNKNOWN: { fg: "#50565D", bg: "#ECECEA", dot: "#8A9097" },
  ONE_OFF: { fg: "#50565D", bg: "#ECECEA", dot: "#8A9097" },
  RECORD: { fg: "#3B5568", bg: "#E3EAF0", dot: "#6C8798" },
};

export function statusLabel(lang: Lang, status: string, issueDate?: string | null): string {
  if (status === "RECORD") return `${t(lang, "RECORD")} · ${fmtDate(lang, issueDate)}`;
  return t(lang, status);
}

export const TIER_LABEL: Record<number, string> = { 0: "TERBUKA", 1: "TERHAD", 2: "SULIT" };

import { useApp } from "../context";
import { t } from "../i18n";
import { STATUS_STYLE, statusLabel } from "../status";

export function StatusBadge({ status, issueDate, title }: { status: string; issueDate?: string | null; title?: string | null }) {
  const { lang } = useApp();
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.UNKNOWN;
  return (
    <span
      title={title ?? undefined}
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded px-2 py-[3px] text-[11px] font-semibold"
      style={{ color: s.fg, background: s.bg }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.dot }} />
      {statusLabel(lang, status, issueDate)}
    </span>
  );
}

export function ConfidenceBadge({ level }: { level: string }) {
  const { lang } = useApp();
  const style =
    level === "HIGH" ? { color: "#1E6B41", background: "#E2F0E7" } : level === "MEDIUM" ? { color: "#7A4F00", background: "#FAEDD0" } : { color: "#50565D", background: "#ECECEA" };
  return (
    <span className="rounded px-2 py-[3px] text-xs font-semibold" style={style}>
      {t(lang, "confidence")}: {t(lang, level)}
    </span>
  );
}

export function TierTag({ tier }: { tier: number }) {
  const restricted = tier > 0;
  return (
    <span className={`font-mono text-[11px] ${restricted ? "font-semibold text-[#9A241C]" : "text-muted"}`}>
      {tier === 0 ? "TERBUKA" : tier === 1 ? "TERHAD" : "SULIT"}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted">
      <span className="pulse h-2 w-2 rounded-full bg-accent" />
      {label}
    </span>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return <div className="rounded-lg border border-[#E8CFCB] bg-[#FCF3F1] px-3.5 py-2.5 text-[13px] text-danger">{message}</div>;
}

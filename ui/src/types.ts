export interface User {
  id: number;
  name: string;
  role: "OFFICER" | "PUBLISHER";
  clearance_level: number;
  clearance_label: string;
  jurisdiction: "FEDERAL" | "SARAWAK";
  grade: string;
  scheme: string;
}

export interface Health {
  status: string;
  mode: "officer" | "publisher";
  inference: { backend: string; reachable: boolean; chat_model?: string; embed_model?: string; chat_model_present?: boolean; embed_model_present?: boolean; detail?: string | null };
  model: { state: "idle" | "loading" | "ready" | "error"; error: string | null };
  embedding_model: string;
  packs_installed: number;
}

export interface Doc {
  id: number;
  circular_no: string;
  series: string;
  title: string;
  issuer: string | null;
  doc_type: string;
  jurisdiction: string;
  cluster: string | null;
  issue_date: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  one_off: number;
  classification_level: number;
  language: string | null;
  applicability: string | null;
  source_url: string | null;
  file_path?: string | null;
  status: string;
  status_reason: string | null;
  owner_verified?: number;
  pack_tier?: number;
  chunk_count?: number;
  vector_count?: number;
}

export interface Source {
  id: string;
  n: number;
  chunk_id: number;
  document_id: number;
  circular_no: string;
  title: string;
  doc_type: string;
  jurisdiction: string;
  status: string;
  status_reason: string | null;
  issue_date: string | null;
  clause_ref: string;
  breadcrumb: string;
  page: number;
  text: string;
  score: number;
  role: "primary" | "comparison";
  tier: number;
}

export interface Excluded {
  document_id: number;
  circular_no: string;
  title: string;
  status_reason: string;
  clause_ref: string;
  issue_date: string | null;
  page: number;
  text: string;
}

export interface ActionLine {
  text: string;
  citations: number[];
  rendered: string;
}

export interface Notification {
  id: number;
  circular_no: string;
  change_type: "STATUS_CHANGE" | "NEW_DOCUMENT";
  summary_ms: string;
  summary_en: string;
  pack_version: number;
  read: number;
  created_at: string;
  document_id: number | null;
  related_doc_id: number | null;
}

export interface InstalledPack {
  tier: number;
  tier_name: string;
  version: number;
  file_path: string;
  sha256: string;
  embedding_model: string;
  installed_at: string;
  previous_version: number | null;
  size_bytes: number;
  embedding_ok: boolean;
}

export interface Inspect {
  docId: number;
  tab: "page" | "lineage" | "changes";
  page?: number;
  highlight?: string;
  diff?: { old: number; new: number };
}

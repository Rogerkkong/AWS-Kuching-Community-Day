// Local API client. The session token arrives once in the window URL (?token=...), is kept in memory
// only, removed from the address bar, and sent as X-Session-Token on every request.

let token: string | null = null;

export function initToken(): string | null {
  const url = new URL(window.location.href);
  const t = url.searchParams.get("token");
  if (t) {
    token = t;
    url.searchParams.delete("token");
    window.history.replaceState(null, "", url.pathname + url.search + url.hash);
  }
  // Website mode: keep the token for this tab only so a page refresh during a demo keeps working.
  try {
    if (token) sessionStorage.setItem("pn-token", token);
    else token = sessionStorage.getItem("pn-token");
  } catch {
    /* storage unavailable: token stays in memory only */
  }
  // Hosted public demo (Vercel): the server runs without a session token; any value is accepted there.
  if (!token) token = "public-demo";
  return token;
}

export function hasToken(): boolean {
  return !!token;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "X-Session-Token": token ?? "" };
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(path, { method, headers, body: payload });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, String(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body ?? {}),
  del: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form),
};

/** Fetch an image with the token header and return an object URL (img src cannot send headers). */
export async function fetchImage(path: string): Promise<{ url: string; pageCount: number; highlights: number }> {
  const res = await fetch(path, { headers: { "X-Session-Token": token ?? "" } });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  const blob = await res.blob();
  return {
    url: URL.createObjectURL(blob),
    pageCount: Number(res.headers.get("X-Page-Count") ?? "1"),
    highlights: Number(res.headers.get("X-Highlights") ?? "0"),
  };
}

/** POST /api/ask and parse the Server-Sent Events stream with fetch (EventSource cannot send headers). */
export async function askStream(
  query: string,
  includeHistorical: boolean,
  onEvent: (event: string, data: any) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "X-Session-Token": token ?? "", "Content-Type": "application/json" },
    body: JSON.stringify({ query, include_historical: includeHistorical }),
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError(res.status, res.statusText);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data.push(line.slice(6));
      }
      if (data.length) onEvent(event, JSON.parse(data.join("\n")));
    }
  }
}

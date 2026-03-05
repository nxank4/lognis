import type {
  AnalysisResultSummary,
  ForensicAnalysisReport,
  LogEntry,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

/** Thrown when the server returns HTTP 429 Too Many Requests. */
export class RateLimitError extends Error {
  readonly retryAfter: number;

  constructor(retryAfter = 60) {
    super("RATE_LIMIT_EXCEEDED");
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
  }
}

/** Parse the Retry-After header value (seconds) with a safe fallback. */
function parseRetryAfter(headers: Headers, fallback = 60): number {
  const raw = headers.get("Retry-After");
  if (!raw) return fallback;
  const parsed = parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

/**
 * Extract a human-readable error message from a FastAPI error response body.
 *
 * FastAPI can return `detail` as a plain string (e.g. custom HTTPException) OR
 * as an array of validation-error objects (HTTP 422 from Pydantic).  Coercing
 * an array with String() produces "[object Object]", so we handle both cases.
 */
function parseDetail(err: unknown, fallback: string): string {
  if (!err || typeof err !== "object") return fallback;
  const { detail } = err as Record<string, unknown>;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // Pydantic validation errors: [{ loc, msg, type }, ...]
    return detail
      .map((d) => {
        if (typeof d === "object" && d !== null && "msg" in d) {
          const loc = Array.isArray((d as Record<string, unknown>).loc)
            ? ((d as Record<string, unknown>).loc as string[]).join(" → ")
            : "";
          return loc ? `${loc}: ${(d as Record<string, unknown>).msg}` : String((d as Record<string, unknown>).msg);
        }
        return String(d);
      })
      .join("; ");
  }
  return String(detail);
}

export async function analyzeForensic(
  entries: LogEntry[],
  userId?: string,
  token?: string
): Promise<ForensicAnalysisReport> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (userId) {
    headers["X-Clerk-User-Id"] = userId;
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: "POST",
    headers,
    body: JSON.stringify(entries),
  });

  if (res.status === 429) {
    throw new RateLimitError(parseRetryAfter(res.headers));
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = parseDetail(await res.json(), detail);
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }

  return res.json() as Promise<ForensicAnalysisReport>;
}

export async function getHistory(
  userId: string,
  token?: string
): Promise<AnalysisResultSummary[]> {
  const headers: Record<string, string> = {
    "X-Clerk-User-Id": userId,
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/v1/history`, { headers });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = parseDetail(await res.json(), detail);
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }

  return res.json() as Promise<AnalysisResultSummary[]>;
}

import axios, { AxiosError } from 'axios';

// '' (empty) means same-origin, which is how production is deployed behind the reverse proxy; only `undefined` falls back.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/** Every failed request rejects with this shape, so callers can tell "offline" from "server said no". */
export class ApiError extends Error {
  status?: number;
  detail: string;
  /** true = no HTTP response at all (no signal, DNS, timeout). false = the server answered with an error. */
  offline: boolean;
  constructor(message: string, opts: { status?: number; offline: boolean }) {
    super(message);
    this.name = 'ApiError';
    this.detail = message;
    this.status = opts.status;
    this.offline = opts.offline;
  }
}

export const isOfflineError = (e: unknown): boolean => e instanceof ApiError && e.offline;

/** FastAPI errors: {detail: "text"} or {detail: [{loc, msg}, ...]} (validation). */
export function messageFromBody(data: any, fallback: string): string {
  const d = data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d.length) {
    return d.map((x: any) => `${(x.loc || []).filter((p: string) => p !== 'body').join('.')}: ${x.msg}`.replace(/^: /, '')).join('; ');
  }
  return fallback;
}

function toApiError(error: AxiosError<any>): ApiError {
  if (!error.response) {
    return new ApiError(error.code === 'ECONNABORTED' ? 'The request timed out.' : 'No connection to the server.', { offline: true });
  }
  const { status, data } = error.response;
  return new ApiError(messageFromBody(data, `Request failed (${status}).`), { status, offline: false });
}

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 15_000,   // rural 3G is slow; "offline" is decided by the network, not by an impatient timer
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT from localStorage on every request
apiClient.interceptors.request.use(config => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Refresh the access token once on 401, then retry the original request.
apiClient.interceptors.response.use(
  r => r,
  async (error: AxiosError<any>) => {
    const cfg: any = error.config;
    if (error.response?.status === 401 && typeof window !== 'undefined' && cfg && !cfg._retried) {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          cfg._retried = true;
          const res = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, { refresh_token: refresh });
          localStorage.setItem('access_token', res.data.access_token);
          cfg.headers['Authorization'] = `Bearer ${res.data.access_token}`;
          return apiClient(cfg);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(toApiError(error));
  },
);

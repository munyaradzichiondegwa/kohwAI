/** snake_case <-> camelCase conversion for API payloads (backend = snake_case, shared types = camelCase). */
const camel = (s: string) => s.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
const snake = (s: string) => s.replace(/[A-Z]/g, c => '_' + c.toLowerCase());

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && Object.getPrototypeOf(v) === Object.prototype;
}

function mapKeys(v: any, f: (k: string) => string): any {
  if (Array.isArray(v)) return v.map(x => mapKeys(x, f));
  if (isPlainObject(v)) return Object.fromEntries(Object.entries(v).map(([k, x]) => [f(k), mapKeys(x, f)]));
  return v;
}

export const toCamel = <T = any>(v: unknown): T => mapKeys(v, camel);
export const toSnake = <T = any>(v: unknown): T => mapKeys(v, snake);

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...options.headers },
  });
  if (!response.ok) {
    let detail = `请求失败 (${response.status})`;
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
    } catch { /* Keep HTTP status when a proxy returns a non-JSON error. */ }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export const post = <T>(path: string, body: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: 'PATCH', body: JSON.stringify(body) });

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function download(path: string, filename: string) {
  const response = await fetch(`/api${path}`);
  if (!response.ok) throw new Error('导出失败，请检查服务连接后重试');
  downloadBlob(await response.blob(), filename);
}

export function csv(table: { columns: string[]; rows: Record<string, unknown>[] }) {
  const escape = (v: unknown) => `"${String(v ?? '').replaceAll('"', '""')}"`;
  return '\uFEFF' + [table.columns.map(escape).join(','), ...table.rows.map(row => table.columns.map(key => escape(row[key])).join(','))].join('\r\n');
}

export function display(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return Number.isFinite(value) ? new Intl.NumberFormat('zh-CN', { maximumSignificantDigits: 8 }).format(value) : String(value);
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

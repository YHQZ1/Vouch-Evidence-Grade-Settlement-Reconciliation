import type { operations } from '../types/generated';
import type {
  ApiError,
  AuditEvent,
  AuditPage,
  CompleteCollection,
  CreateBatchRequest,
  ExceptionRecord,
  ExceptionPage,
  AgentRun,
  JsonSuccess,
  Page,
  SettlementResult,
  SourceKind,
  SettlementPage,
} from '../types/api';
import { fetchAllPages } from './pagination';

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

function assertSafeNumbers(value: unknown): void {
  if (
    typeof value === 'number' &&
    !Number.isSafeInteger(value) &&
    Number.isInteger(value)
  ) {
    throw new Error('Unsafe integer received from API');
  }
  if (Array.isArray(value)) value.forEach(assertSafeNumbers);
  else if (value && typeof value === 'object') {
    Object.values(value).forEach(assertSafeNumbers);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    signal,
    headers: { Accept: 'application/json', ...init.headers },
  });
  const contentType = response.headers.get('content-type') ?? '';
  const body =
    response.status === 204
      ? null
      : contentType.includes('json')
        ? await response.json()
        : await response.text();
  if (!response.ok) {
    const error = body as { error?: ApiError };
    throw new ApiRequestError(
      response.status,
      error?.error?.code ?? 'REQUEST_FAILED',
      error?.error?.message ?? 'The API request failed',
    );
  }
  if (body !== null) assertSafeNumbers(body);
  return body as T;
}

type OperationResult<Operation extends keyof operations> = JsonSuccess<Operation>;

function pagePath(
  id: string,
  resource: 'settlements' | 'exceptions' | 'audit-events',
  offset: number,
  query = '',
) {
  return `/api/v1/batches/${encodeURIComponent(id)}/${resource}?offset=${offset}${query}`;
}

function getFilename(header: string | null, fallback: string): string {
  const utf8 = header?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (utf8) return decodeURIComponent(utf8.replace(/^"|"$/g, ''));
  return header?.match(/filename="?([^";]+)"?/i)?.[1] ?? fallback;
}

export const api = {
  createBatch: (clock: string, signal?: AbortSignal) =>
    request<OperationResult<'createBatch'>>(
      '/api/v1/batches',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evaluation_clock: clock } satisfies CreateBatchRequest),
      },
      signal,
    ),
  getBatch: (id: string, signal?: AbortSignal) =>
    request<OperationResult<'getBatch'>>(
      `/api/v1/batches/${encodeURIComponent(id)}`,
      {},
      signal,
    ),
  upload: (id: string, kind: SourceKind, file: File, signal?: AbortSignal) =>
    request<OperationResult<'putBatchSource'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/sources/${kind}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': kind === 'policy' ? 'application/json' : 'text/csv',
          'X-Source-Filename': file.name,
        },
        body: file,
      },
      signal,
    ),
  run: (id: string, signal?: AbortSignal) =>
    request<OperationResult<'runReconciliation'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/reconciliation-runs`,
      { method: 'POST' },
      signal,
    ),
  getResult: (id: string, signal?: AbortSignal) =>
    request<OperationResult<'getReconciliationResult'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/result`,
      {},
      signal,
    ),
  getCloseReadiness: (id: string, signal?: AbortSignal) =>
    request<OperationResult<'getCloseReadiness'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/close-readiness`,
      {},
      signal,
    ),
  listSettlementsPage: (id: string, offset: number, signal?: AbortSignal) =>
    request<SettlementPage>(pagePath(id, 'settlements', offset), {}, signal),
  listSettlements: async (id: string, signal?: AbortSignal) =>
    fetchAllPages<SettlementResult>(
      (offset) => api.listSettlementsPage(id, offset, signal),
      (item) => item.aggregate.settlement_id,
      'Settlement',
    ),
  getSettlement: (id: string, settlementId: string, signal?: AbortSignal) =>
    request<OperationResult<'getSettlement'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/settlements/${encodeURIComponent(settlementId)}`,
      {},
      signal,
    ),
  listExceptionsPage: (id: string, offset: number, signal?: AbortSignal) =>
    request<ExceptionPage>(pagePath(id, 'exceptions', offset), {}, signal),
  listExceptions: async (id: string, signal?: AbortSignal) =>
    fetchAllPages<ExceptionRecord>(
      (offset) => api.listExceptionsPage(id, offset, signal),
      (item) => item.exception_id,
      'Exception',
    ),
  listAuditPage: (id: string, offset: number, signal?: AbortSignal) =>
    request<AuditPage>(pagePath(id, 'audit-events', offset), {}, signal),
  listAudit: async (id: string, signal?: AbortSignal) =>
    fetchAllPages<AuditEvent>(
      (offset) => api.listAuditPage(id, offset, signal),
      (item) => item.audit_id,
      'Audit',
    ),
  runInvestigation: (id: string, settlementId: string, signal?: AbortSignal) =>
    request<OperationResult<'runInvestigation'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/settlements/${encodeURIComponent(settlementId)}/investigations`,
      { method: 'POST' },
      signal,
    ),
  listInvestigationsPage: (
    id: string,
    settlementId: string,
    offset: number,
    signal?: AbortSignal,
  ) =>
    request<OperationResult<'listSettlementInvestigations'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/settlements/${encodeURIComponent(settlementId)}/investigations?offset=${offset}`,
      { method: 'GET' },
      signal,
    ),
  listInvestigations: async (id: string, settlementId: string, signal?: AbortSignal) =>
    fetchAllPages<AgentRun>(
      (offset) => api.listInvestigationsPage(id, settlementId, offset, signal),
      (item) => item.run_id,
      'Investigation',
    ),
  listBatchInvestigationsPage: (id: string, offset: number, signal?: AbortSignal) =>
    request<OperationResult<'listBatchInvestigations'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/investigations?offset=${offset}`,
      {},
      signal,
    ),
  listBatchInvestigations: async (id: string, signal?: AbortSignal) =>
    fetchAllPages<AgentRun>(
      (offset) => api.listBatchInvestigationsPage(id, offset, signal),
      (item) => item.run_id,
      'Investigation',
    ),
  getInvestigationEligibility: (
    id: string,
    settlementId: string,
    signal?: AbortSignal,
  ) =>
    request<OperationResult<'getInvestigationEligibility'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/settlements/${encodeURIComponent(settlementId)}/investigations/eligibility`,
      {},
      signal,
    ),
  getEffectiveReview: (id: string, settlementId: string, signal?: AbortSignal) =>
    request<OperationResult<'getEffectiveReview'>>(
      `/api/v1/batches/${encodeURIComponent(id)}/settlements/${encodeURIComponent(settlementId)}/effective-review`,
      {},
      signal,
    ),
};

export async function downloadExport(
  id: string,
  artifact: 'reconciliation-result' | 'exceptions' | 'audit-events' | 'investigations',
): Promise<string> {
  const response = await fetch(
    `/api/v1/batches/${encodeURIComponent(id)}/exports/${artifact}`,
    { headers: { Accept: 'application/json' } },
  );
  if (!response.ok) {
    const body = (await response.json()) as { error?: ApiError };
    throw new ApiRequestError(
      response.status,
      body.error?.code ?? 'EXPORT_FAILED',
      body.error?.message ?? 'Export failed',
    );
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  const filename = getFilename(
    response.headers.get('content-disposition'),
    `vouch-${artifact}.json`,
  );
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = 'noopener';
  anchor.style.display = 'none';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
  return filename;
}

export type { CompleteCollection, Page };

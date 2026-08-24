const STORAGE_PREFIX = 'vouch:batch-ref:';

export function publicBatchRef(batchId: string): string {
  const raw = batchId.startsWith('batch_api_')
    ? batchId.slice('batch_api_'.length)
    : batchId;
  return raw.slice(0, 12);
}

export function rememberBatchRef(batchId: string): string {
  const ref = publicBatchRef(batchId);
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(`${STORAGE_PREFIX}${ref}`, batchId);
  }
  return ref;
}

export function resolveBatchId(ref: string | undefined): string | undefined {
  if (!ref) return undefined;
  if (ref.startsWith('batch_api_')) return ref;
  if (typeof window === 'undefined') return ref;
  return window.sessionStorage.getItem(`${STORAGE_PREFIX}${ref}`) ?? ref;
}

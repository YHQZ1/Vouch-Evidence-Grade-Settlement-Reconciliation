import {
  AlertTriangle,
  Check,
  FileJson,
  FileSpreadsheet,
  Fingerprint,
  LoaderCircle,
  LockKeyhole,
} from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiRequestError, api } from '../../lib/api';
import { formatBytes } from '../../lib/format';
import { SOURCE_LABELS } from '../../lib/labels';
import type { BatchResponse, SourceKind, SourceResponse } from '../../types/api';
import { Button, CopyValue } from '../../components/ui';

const PRESET = '2026-08-31T18:30:00Z';
type Slot = {
  file: File | null;
  source: SourceResponse | null;
  status: 'idle' | 'uploading' | 'uploaded' | 'failed';
  error?: string;
};
const emptySlots = (): Record<SourceKind, Slot> => ({
  gateway: { file: null, source: null, status: 'idle' },
  bank: { file: null, source: null, status: 'idle' },
  ledger: { file: null, source: null, status: 'idle' },
  policy: { file: null, source: null, status: 'idle' },
});
const SLOT_CLASSES = {
  idle: 'border-line',
  uploading: 'border-amber/50 bg-amber/5',
  uploaded: 'border-sage/40 bg-sage/5',
  failed: 'border-coral/40 bg-coral/5',
} as const;

export function BatchSetupPage() {
  const navigate = useNavigate();
  const [clock, setClock] = useState(PRESET);
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [slots, setSlots] = useState<Record<SourceKind, Slot>>(emptySlots);
  const [creating, setCreating] = useState(false);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState('');
  const inputRefs = useRef<Record<SourceKind, HTMLInputElement | null>>({
    gateway: null,
    bank: null,
    ledger: null,
    policy: null,
  });
  const controllers = useRef(new Map<SourceKind, AbortController>());
  const allUploaded = useMemo(
    () =>
      Object.values(slots).every(
        (slot) => slot.status === 'uploaded' && slot.source !== null,
      ),
    [slots],
  );
  const uploading = Object.values(slots).some((slot) => slot.status === 'uploading');
  const canRun = batch?.status === 'ready' && allUploaded && !running && !uploading;

  async function createBatch() {
    if (creating || batch || uploading || running) return;
    setCreating(true);
    setMessage('');
    try {
      const response = await api.createBatch(clock);
      setBatch(response);
      setSlots(emptySlots());
      setRunning(false);
      setMessage(
        `Batch ${response.batch_id} created. Add four immutable evidence sources.`,
      );
    } catch (error) {
      setMessage(
        error instanceof ApiRequestError
          ? `${error.code}: ${error.message}`
          : 'Could not create batch.',
      );
    } finally {
      setCreating(false);
    }
  }

  function startNewBatch() {
    if (creating || uploading || running) return;
    controllers.current.forEach((controller) => controller.abort());
    controllers.current.clear();
    setBatch(null);
    setSlots(emptySlots());
    setRunning(false);
    setMessage(
      'Previous batch cleared locally. Create a new batch to begin a fresh upload set.',
    );
  }

  function choose(kind: SourceKind, file: File | undefined) {
    if (!file || !batch || slots[kind].status === 'uploaded') return;
    setSlots((current) => ({
      ...current,
      [kind]: { file, source: null, status: 'idle' },
    }));
    void upload(kind, file, batch.batch_id);
  }

  async function upload(kind: SourceKind, file: File, batchId: string) {
    const controller = new AbortController();
    controllers.current.set(kind, controller);
    setSlots((current) => ({
      ...current,
      [kind]: { ...current[kind], status: 'uploading', error: undefined },
    }));
    try {
      const response = await api.upload(batchId, kind, file, controller.signal);
      setSlots((current) => ({
        ...current,
        [kind]: { file, source: response.source, status: 'uploaded' },
      }));
      setBatch((current) =>
        current?.batch_id === batchId
          ? {
              ...current,
              status: response.status,
              sources: [
                ...current.sources.filter((item) => item.source_kind !== kind),
                response.source,
              ],
            }
          : current,
      );
      setMessage(`${file.name} uploaded and fingerprinted.`);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      const text =
        error instanceof ApiRequestError
          ? `${error.code}: ${error.message}`
          : 'Upload failed. The server did not accept this source.';
      setSlots((current) => ({
        ...current,
        [kind]: { ...current[kind], status: 'failed', error: text },
      }));
      setMessage(text);
    } finally {
      controllers.current.delete(kind);
    }
  }

  async function run() {
    if (!batch || !canRun) return;
    const batchId = batch.batch_id;
    setRunning(true);
    setMessage('Running deterministic reconciliation…');
    try {
      const response = await api.run(batchId);
      if (response.status === 'failed' || !response.result_available) {
        setBatch((current) =>
          current?.batch_id === batchId
            ? { ...current, status: response.status, failure: response.failure }
            : current,
        );
        setMessage(
          `${response.failure?.code ?? 'RUN_FAILED'}: ${response.failure?.message ?? 'Reconciliation failed.'}`,
        );
        return;
      }
      navigate(`/batches/${batchId}/overview`);
    } catch (error) {
      setMessage(
        error instanceof ApiRequestError
          ? `${error.code}: ${error.message}`
          : 'Reconciliation could not be completed.',
      );
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl" id="main-content">
      <div className="mb-8 max-w-3xl">
        <div className="mb-5 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-teal">
          <span className="grid h-7 w-7 place-items-center rounded-full bg-teal text-white">
            V
          </span>{' '}
          Evidence ledger / Phase 7
        </div>
        <h1 className="font-serif text-4xl leading-tight sm:text-6xl">
          Prove the batch before the books close.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-muted">
          Load the four source records that explain how Razorpay activity moved through
          the bank and ledger. Vouch keeps the evidence immutable and puts deterministic
          controls in charge.
        </p>
      </div>
      <section
        className="border border-line bg-panel p-5 sm:p-7"
        aria-labelledby="clock-title"
      >
        <div className="flex items-start justify-between gap-5">
          <div>
            <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
              Step 01 / Scope
            </p>
            <h2 id="clock-title" className="font-serif text-2xl">
              Set the evaluation clock
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              The clock is part of the proof. It fixes timing decisions and makes the
              run reproducible.
            </p>
          </div>
          <LockKeyhole size={22} className="text-teal" aria-hidden="true" />
        </div>
        <div className="mt-6 grid gap-3 lg:grid-cols-[1fr_auto_auto] lg:items-end">
          <label className="block text-sm font-bold" htmlFor="clock">
            Evaluation clock{' '}
            <span className="ml-1 text-xs font-normal text-coral">required</span>
            <input
              className="mt-2 block w-full rounded-sm border border-line bg-paper px-3 py-2.5 font-mono text-sm"
              id="clock"
              type="datetime-local"
              value={clock.slice(0, 16)}
              onChange={(event) => setClock(`${event.target.value}:00Z`)}
            />
          </label>
          <button
            className="rounded-sm border border-line px-3 py-2.5 text-left text-xs text-muted hover:border-teal hover:text-teal"
            type="button"
            onClick={() => setClock(PRESET)}
          >
            <span className="block font-mono">{PRESET}</span>
            <span>Frozen demonstration preset</span>
          </button>
          {batch ? (
            <Button
              variant="secondary"
              disabled={uploading || running}
              onClick={startNewBatch}
            >
              Start a new batch
            </Button>
          ) : (
            <Button disabled={creating || !clock} onClick={() => void createBatch()}>
              {creating ? (
                <>
                  <LoaderCircle className="animate-spin" size={16} /> Creating
                </>
              ) : (
                'Create batch'
              )}
            </Button>
          )}
        </div>
      </section>
      {batch && (
        <section
          className="mt-5 border border-line bg-panel p-5 sm:p-7"
          aria-labelledby="sources-title"
        >
          <div className="flex items-start justify-between gap-5">
            <div>
              <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
                Step 02 / Evidence
              </p>
              <h2 id="sources-title" className="font-serif text-2xl">
                Attach immutable source records
              </h2>
              <p className="mt-2 text-sm leading-6 text-muted">
                Each slot uploads independently. A conflicting replacement remains
                visibly rejected.
              </p>
            </div>
            <Fingerprint size={22} className="text-teal" aria-hidden="true" />
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            {(['gateway', 'bank', 'ledger', 'policy'] as SourceKind[]).map((kind) => (
              <SourceSlot
                key={kind}
                kind={kind}
                slot={slots[kind]}
                inputRef={(element) => {
                  inputRefs.current[kind] = element;
                }}
                onChoose={(file) => choose(kind, file)}
                onRetry={() =>
                  slots[kind].file &&
                  void upload(kind, slots[kind].file!, batch.batch_id)
                }
              />
            ))}
          </div>
          <div className="mt-6 flex flex-col justify-between gap-4 border-t border-line pt-5 sm:flex-row sm:items-end">
            <div>
              <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.16em] text-muted">
                Lifecycle
              </p>
              <strong className="capitalize">
                {batch.status.replaceAll('_', ' ')}
              </strong>
              <p className="mt-1 text-sm text-muted">
                {allUploaded
                  ? 'All four sources are present. The server reports this batch ready.'
                  : 'Upload all four source records to unlock reconciliation.'}
              </p>
              {batch.failure && (
                <p className="mt-2 text-sm font-bold text-coral" role="alert">
                  {batch.failure.code}: {batch.failure.message}
                </p>
              )}
            </div>
            <Button onClick={() => void run()} disabled={!canRun}>
              {running ? (
                <>
                  <LoaderCircle className="animate-spin" size={16} /> Running controls
                </>
              ) : (
                'Run reconciliation'
              )}
            </Button>
          </div>
        </section>
      )}
      <div className="mt-5 grid gap-3 text-sm text-muted sm:grid-cols-2">
        <div className="flex gap-2 border border-line bg-panel p-4">
          <Check size={17} className="shrink-0 text-sage" aria-hidden="true" />
          <span>
            Raw source bytes are retained by the API and never rewritten in the browser.
          </span>
        </div>
        <div className="flex gap-2 border border-line bg-panel p-4">
          <LockKeyhole size={17} className="shrink-0 text-teal" aria-hidden="true" />
          <span>
            Local demonstration only: batches disappear after a backend restart.
          </span>
        </div>
      </div>
      <p className="mt-4 text-sm text-ink" aria-live="polite">
        {message}
      </p>
    </main>
  );
}

function SourceSlot({
  kind,
  slot,
  inputRef,
  onChoose,
  onRetry,
}: {
  kind: SourceKind;
  slot: Slot;
  inputRef: (element: HTMLInputElement | null) => void;
  onChoose: (file: File | undefined) => void;
  onRetry: () => void;
}) {
  const Icon = kind === 'policy' ? FileJson : FileSpreadsheet;
  const description =
    kind === 'policy'
      ? 'Versioned rules and materiality'
      : kind === 'gateway'
        ? 'Settlement movements and UTRs'
        : kind === 'bank'
          ? 'Credits, dates and references'
          : 'Journal-level postings and controls';
  return (
    <article
      className={`flex min-h-48 flex-col justify-between border p-4 ${SLOT_CLASSES[slot.status]}`}
    >
      <div className="flex gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded bg-teal/10 text-teal">
          <Icon size={20} aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <h3 className="font-bold">{SOURCE_LABELS[kind]}</h3>
          <p className="mt-1 text-sm text-muted">{description}</p>
          {slot.file ? (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="max-w-full truncate font-mono">{slot.file.name}</span>
              <span>{formatBytes(slot.file.size)}</span>
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted">CSV / JSON source required</p>
          )}
          {slot.source && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-sage">
              <span>
                <Check size={13} className="mr-1 inline" aria-hidden="true" />
                sequence {slot.source.sequence}
              </span>
              <CopyValue
                value={slot.source.sha256}
                label={`Copy ${slot.file?.name ?? kind} SHA-256`}
              />
            </div>
          )}
          {slot.error && (
            <p className="mt-3 text-xs text-coral" role="alert">
              <AlertTriangle size={14} className="mr-1 inline" aria-hidden="true" />
              {slot.error}
            </p>
          )}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between gap-2">
        {slot.status === 'uploaded' ? (
          <span className="flex items-center gap-1 text-sm font-bold text-sage">
            <Check size={16} /> Uploaded
          </span>
        ) : slot.status === 'uploading' ? (
          <span className="flex items-center gap-2 text-sm text-amber" role="status">
            <LoaderCircle className="animate-spin" size={18} /> Uploading
          </span>
        ) : (
          <>
            <input
              className="sr-only"
              ref={inputRef}
              id={`file-${kind}`}
              type="file"
              accept={kind === 'policy' ? '.json,application/json' : '.csv,text/csv'}
              onChange={(event) => onChoose(event.target.files?.[0])}
            />
            <label
              className="inline-flex cursor-pointer items-center rounded-sm border border-line bg-panel px-3 py-2 text-sm font-bold text-teal hover:border-teal"
              htmlFor={`file-${kind}`}
            >
              {slot.status === 'failed' ? 'Choose again' : 'Choose file'}
            </label>
            {slot.status === 'failed' && (
              <button
                className="text-xs font-bold text-coral underline"
                type="button"
                onClick={onRetry}
              >
                Retry same file
              </button>
            )}
          </>
        )}
      </div>
    </article>
  );
}

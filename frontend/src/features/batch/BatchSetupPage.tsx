import {
  AlertTriangle,
  Check,
  FileJson,
  FileSpreadsheet,
  LoaderCircle,
  LockKeyhole,
} from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiRequestError, api } from '../../lib/api';
import { formatBytes } from '../../lib/format';
import { rememberBatchRef } from '../../lib/batch-ref';
import { SOURCE_LABELS } from '../../lib/labels';
import type { BatchResponse, SourceKind, SourceResponse } from '../../types/api';
import { Button, CopyValue, VouchMark } from '../../components/ui';

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
  const uploadedCount = Object.values(slots).filter(
    (slot) => slot.status === 'uploaded',
  ).length;
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
      navigate(`/batches/${rememberBatchRef(batchId)}/overview`);
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
    <main className="w-full px-4 py-8 sm:px-6 sm:py-10 lg:px-8" id="main-content">
      <section
        className="mb-8 grid items-center gap-10 border-b border-line pb-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)] lg:gap-16"
        aria-labelledby="intro-title"
      >
        <div>
          <div className="mb-6 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.16em] text-teal">
            <VouchMark className="h-12 w-12" />
            <span className="text-xl font-medium tracking-[0.14em]">Vouch</span>
          </div>
          <h1
            id="intro-title"
            className="max-w-2xl font-sans font-light tracking-tight text-4xl leading-[1.08] sm:text-6xl"
          >
            Reconcile a payment batch before the books close.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-muted">
            Vouch checks one payment event across your gateway, bank and ledger files.
            It links the evidence, flags what conflicts or is still missing, and shows
            the reason behind every decision.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2" aria-label="How to use Vouch">
            <div className="flex items-baseline gap-3">
              <span className="shrink-0 font-mono text-xs leading-6 text-teal">01</span>
              <div>
                <h2 className="text-sm font-semibold leading-6">Set the clock</h2>
                <p className="mt-1 text-sm leading-6 text-muted">
                  Choose the evaluation time used for SLA and timing checks.
                </p>
              </div>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="shrink-0 font-mono text-xs leading-6 text-teal">02</span>
              <div>
                <h2 className="text-sm font-semibold leading-6">Upload four sources</h2>
                <p className="mt-1 text-sm leading-6 text-muted">
                  Add gateway, bank, ledger and policy CSV/JSON files.
                </p>
              </div>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="shrink-0 font-mono text-xs leading-6 text-teal">03</span>
              <div>
                <h2 className="text-sm font-semibold leading-6">Run the controls</h2>
                <p className="mt-1 text-sm leading-6 text-muted">
                  Vouch matches records without changing your original files.
                </p>
              </div>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="shrink-0 font-mono text-xs leading-6 text-teal">04</span>
              <div>
                <h2 className="text-sm font-semibold leading-6">Review and export</h2>
                <p className="mt-1 text-sm leading-6 text-muted">
                  Inspect proof, resolve exceptions, then export the audit trail.
                </p>
              </div>
            </div>
          </div>
        </div>
        <figure
          className="relative min-h-[320px] overflow-hidden border-l border-line px-5 py-8 sm:px-8"
          aria-labelledby="flow-title"
        >
          <div className="relative flex h-full min-h-[260px] flex-col justify-between">
            <figcaption
              id="flow-title"
              className="text-xs font-semibold uppercase tracking-[0.16em] text-muted"
            >
              One event / three proofs
            </figcaption>
            <svg
              className="absolute inset-x-0 top-1/2 h-28 w-full -translate-y-1/2"
              viewBox="0 0 520 120"
              fill="none"
              role="img"
              aria-label="Gateway activity flows to bank movement and ledger posting"
            >
              <path
                d="M92 60H218M302 60H428"
                stroke="var(--color-teal)"
                strokeWidth="2"
                strokeDasharray="5 7"
              />
              <path
                d="m205 52 13 8-13 8M415 52l13 8-13 8"
                stroke="var(--color-teal)"
                strokeWidth="2"
                strokeLinecap="square"
                strokeLinejoin="miter"
              />
              <circle cx="64" cy="60" r="28" fill="var(--color-teal-dark)" />
              <circle cx="260" cy="60" r="28" fill="var(--color-electric)" />
              <circle cx="456" cy="60" r="28" fill="var(--color-teal-dark)" />
              <path d="M52 48h14l10 10-10 10H52l10-10-10-10Z" fill="white" />
              <path
                d="M248 48h14l10 10-10 10h-14l10-10-10-10Z"
                fill="var(--color-teal-dark)"
              />
              <path d="M444 48h14l10 10-10 10h-14l10-10-10-10Z" fill="white" />
            </svg>
            <div className="relative grid grid-cols-3 gap-2 text-center text-xs">
              <div>
                <p className="font-semibold text-ink">Gateway</p>
                <p className="mt-1 text-muted">what was charged</p>
              </div>
              <div>
                <p className="font-semibold text-ink">Bank</p>
                <p className="mt-1 text-muted">what arrived</p>
              </div>
              <div>
                <p className="font-semibold text-ink">Ledger</p>
                <p className="mt-1 text-muted">what was posted</p>
              </div>
            </div>
          </div>
        </figure>
      </section>
      <section
        className="border-y border-line py-8 sm:py-10"
        aria-labelledby="clock-title"
      >
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(420px,0.9fr)] lg:items-end lg:gap-14">
          <div>
            <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
              Step 01 / Scope
            </p>
            <h2
              id="clock-title"
              className="font-sans font-light tracking-tight text-2xl sm:text-3xl"
            >
              Set the evaluation clock
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
              The clock is part of the proof. It fixes timing decisions and makes the
              run reproducible.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-[minmax(280px,360px)_minmax(170px,auto)] sm:items-end">
            <label className="block text-sm font-semibold" htmlFor="clock">
              Evaluation clock
              <span className="ml-1 text-xs font-normal text-coral">required</span>
              <input
                className="mt-2 block h-12 w-full rounded-sm border border-line bg-paper px-3 font-mono text-sm shadow-none"
                id="clock"
                type="datetime-local"
                value={clock.slice(0, 16)}
                onChange={(event) => setClock(`${event.target.value}:00Z`)}
              />
            </label>
            {batch ? (
              <Button
                className="h-12 min-w-[170px] whitespace-nowrap"
                variant="secondary"
                disabled={uploading || running}
                onClick={startNewBatch}
              >
                Start a new batch
              </Button>
            ) : (
              <Button
                className="h-12 min-w-[170px] whitespace-nowrap"
                disabled={creating || !clock}
                onClick={() => void createBatch()}
              >
                {creating ? (
                  <>
                    <LoaderCircle className="animate-spin" size={16} /> Creating
                  </>
                ) : (
                  'Create batch'
                )}
              </Button>
            )}
            <button
              className="text-left text-xs text-muted underline decoration-line underline-offset-4 hover:text-teal sm:col-span-2"
              type="button"
              onClick={() => setClock(PRESET)}
            >
              Frozen demonstration preset: <span className="font-mono">{PRESET}</span>
            </button>
          </div>
        </div>
      </section>
      {batch && (
        <section
          className="mt-8 border-y border-line py-8 sm:py-10"
          aria-labelledby="sources-title"
        >
          <div className="flex flex-col gap-5 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
                Step 02 / Evidence
              </p>
              <h2
                id="sources-title"
                className="font-sans font-light tracking-tight text-2xl sm:text-3xl"
              >
                Attach immutable source records
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                Upload the original gateway, bank, ledger and policy files. Vouch
                fingerprints every upload, preserves the raw bytes, and will not let a
                conflicting replacement overwrite evidence.
              </p>
            </div>
            <div className="shrink-0 font-mono text-sm text-muted">
              <span className="font-semibold text-teal">{uploadedCount}/4</span> sources
              uploaded
            </div>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {(['gateway', 'bank', 'ledger', 'policy'] as SourceKind[]).map(
              (kind, index) => (
                <SourceSlot
                  key={kind}
                  kind={kind}
                  index={index + 1}
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
              ),
            )}
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
  index,
  slot,
  inputRef,
  onChoose,
  onRetry,
}: {
  kind: SourceKind;
  index: number;
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
        <div className="flex w-10 shrink-0 flex-col items-center gap-2">
          <span className="font-mono text-xs font-semibold text-teal">
            {String(index).padStart(2, '0')}
          </span>
          <div className="grid h-9 w-9 place-items-center rounded bg-teal/10 text-teal">
            <Icon size={20} aria-hidden="true" />
          </div>
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

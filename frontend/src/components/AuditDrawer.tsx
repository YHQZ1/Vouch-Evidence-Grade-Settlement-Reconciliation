import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { api } from '../lib/api';
import { formatCalculatedValue } from '../lib/format';
import type { AuditEvent } from '../types/api';
import { CopyList, CopyValue, EvidenceBadge, ReasonCodes } from './ui';

export function AuditDrawer({
  batchId,
  settlementId,
  trigger,
}: {
  batchId: string;
  settlementId?: string;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const requestControllerRef = useRef<AbortController | null>(null);
  const titleId = `audit-title-${useId().replaceAll(':', '')}`;
  const descriptionId = `audit-description-${useId().replaceAll(':', '')}`;

  const loadEvents = useCallback(
    async (signal: AbortSignal) => {
      setLoading(true);
      setError(null);
      setEvents([]);
      try {
        const result = await api.listAudit(batchId, signal);
        setEvents(
          result.items
            .filter((event) => !settlementId || event.settlement_id === settlementId)
            .sort((a, b) => a.sequence_number - b.sequence_number),
        );
      } catch (caught) {
        if (!(caught instanceof Error && caught.name === 'AbortError')) {
          setError(
            caught instanceof Error
              ? caught
              : new Error('Audit evidence could not be loaded.'),
          );
        }
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    },
    [batchId, settlementId],
  );

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    requestControllerRef.current = controller;
    void loadEvents(controller.signal);
    return () => {
      controller.abort();
      if (requestControllerRef.current === controller)
        requestControllerRef.current = null;
    };
  }, [open, loadEvents]);

  useEffect(() => {
    if (!open) return;
    const focusDialog = () => dialogRef.current?.focus();
    const frame = window.requestAnimationFrame(focusDialog);
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;
      const focusable = [
        ...dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ];
      if (!focusable.length) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          document.activeElement === dialogRef.current)
      ) {
        event.preventDefault();
        last.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          document.activeElement === dialogRef.current)
      ) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener('keydown', onKey);
    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  function close() {
    requestControllerRef.current?.abort();
    setOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="inline-flex items-center gap-2 rounded-sm border border-line bg-panel px-3 py-2 text-sm font-bold text-teal hover:border-teal"
        onClick={() => setOpen(true)}
      >
        {trigger}
      </button>
      {open && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-ink/45"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) close();
          }}
        >
          <section
            ref={dialogRef}
            className="flex h-full w-full max-w-2xl flex-col overflow-hidden bg-panel shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            tabIndex={-1}
          >
            <div className="flex items-start justify-between gap-4 border-b border-line p-5 sm:p-7">
              <div>
                <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
                  Append-only decision trail
                </p>
                <h2 id={titleId} className="font-serif text-3xl">
                  Audit explanation
                </h2>
                <p
                  id={descriptionId}
                  className="mt-2 max-w-xl text-sm leading-6 text-muted"
                >
                  Deterministic events are shown in sequence order. Proposed evidence is
                  never treated as verified.
                </p>
              </div>
              <button
                className="rounded-sm p-2 text-muted hover:bg-paper hover:text-ink"
                type="button"
                aria-label="Close audit explanation"
                onClick={close}
              >
                <X />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 sm:p-7">
              {loading ? (
                <p className="text-sm text-muted" role="status">
                  Loading audit evidence…
                </p>
              ) : error ? (
                <div className="border border-coral/40 bg-coral/5 p-4" role="alert">
                  <p className="font-bold text-coral">Audit evidence unavailable</p>
                  <p className="mt-1 text-sm">{error.message}</p>
                  <button
                    className="mt-3 rounded-sm border border-coral/40 px-3 py-2 text-sm font-bold text-coral hover:bg-coral/10"
                    type="button"
                    onClick={() => {
                      const controller = new AbortController();
                      requestControllerRef.current = controller;
                      void loadEvents(controller.signal);
                    }}
                  >
                    Retry
                  </button>
                </div>
              ) : events.length === 0 ? (
                <p className="text-sm text-muted">
                  No audit events cite this settlement.
                </p>
              ) : (
                <div className="space-y-3">
                  {events.map((event) => (
                    <AuditEventRow key={event.audit_id} event={event} />
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function AuditEventRow({ event }: { event: AuditEvent }) {
  const [expanded, setExpanded] = useState(false);
  const status =
    event.candidate_accepted === true
      ? 'verified'
      : event.candidate_accepted === false
        ? 'rejected'
        : null;
  return (
    <article className="border border-line bg-paper">
      <button
        className="flex w-full items-center gap-3 p-4 text-left hover:bg-white"
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        <span className="font-mono text-xs text-muted">#{event.sequence_number}</span>
        <span className="min-w-0 flex-1">
          <strong className="block capitalize">
            {event.decision_type.replaceAll('_', ' ')}
          </strong>
          <small className="block truncate text-muted">
            {event.resulting_state ?? 'batch event'} · {event.settlement_id ?? 'batch'}
          </small>
        </span>
        {status && <EvidenceBadge status={status} />}
        {expanded ? (
          <ChevronUp size={17} aria-hidden="true" />
        ) : (
          <ChevronDown size={17} aria-hidden="true" />
        )}
      </button>
      {expanded && (
        <div className="space-y-5 border-t border-line p-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span>
              {event.prior_state ?? '—'} → {event.resulting_state ?? '—'}
            </span>
            {status && <EvidenceBadge status={status} />}
          </div>
          <ReasonCodes codes={event.reason_codes} />
          <dl className="grid gap-3 sm:grid-cols-2">
            <Meta label="Audit ID">
              <CopyValue value={event.audit_id} label="Copy audit ID" />
            </Meta>
            <Meta label="Decision type">
              <span className="font-mono text-xs">{event.decision_type}</span>
            </Meta>
            <Meta label="Rule">
              <span className="font-mono text-xs">
                {event.rule_id} / {event.rule_version}
              </span>
            </Meta>
            <Meta label="Policy / schema">
              <span className="font-mono text-xs">
                {event.policy_version} / {event.schema_version}
              </span>
            </Meta>
            <Meta label="Evaluation clock">
              <span className="font-mono text-xs">{event.evaluation_clock}</span>
            </Meta>
            <Meta label="Candidate score">
              <span className="font-mono text-xs">{event.candidate_score ?? '—'}</span>
            </Meta>
          </dl>
          <div>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-muted">
              Decision-cited source IDs
            </h3>
            <CopyList values={event.cited_source_record_ids} />
          </div>
          <div>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-muted">
              Input fingerprints
            </h3>
            <CopyList
              values={event.input_fingerprints}
              label="Copy input fingerprint"
            />
          </div>
          <div>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-muted">
              Calculated values
            </h3>
            <CalculatedEventValues values={event.calculated_values} />
          </div>
          {event.candidate_signals.length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-muted">
                Candidate signals
              </h3>
              <div className="flex flex-wrap gap-2">
                {event.candidate_signals.map((signal) => (
                  <span
                    key={signal.name}
                    className={`rounded border px-2 py-1 text-xs ${signal.satisfied ? 'border-sage/30 bg-sage/10 text-sage' : 'border-coral/30 bg-coral/10 text-coral'}`}
                  >
                    {signal.name}: {signal.value} · weight {signal.weight}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}

function CalculatedEventValues({
  values,
}: {
  values: { name: string; value: string }[];
}) {
  return values.length ? (
    <div className="grid gap-2 sm:grid-cols-2">
      {values.map((value) => (
        <div className="rounded border border-line bg-white p-2" key={value.name}>
          <span className="block font-mono text-[11px] text-muted">{value.name}</span>
          <strong
            className={`mt-1 block break-all font-mono text-sm ${value.name.endsWith('_subunits') ? 'text-ink' : 'text-teal'}`}
          >
            {renderCalculated(value.name, value.value)}
          </strong>
        </div>
      ))}
    </div>
  ) : (
    <span className="text-sm text-muted">None</span>
  );
}

function renderCalculated(name: string, value: string) {
  try {
    return formatCalculatedValue(name, value);
  } catch {
    return <span className="text-coral">Invalid monetary value: {value}</span>;
  }
}

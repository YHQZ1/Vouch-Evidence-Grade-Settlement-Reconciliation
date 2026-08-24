import {
  AlertTriangle,
  Check,
  CircleAlert,
  Copy,
  Info,
  LoaderCircle,
  ShieldCheck,
} from 'lucide-react';
import { useState } from 'react';
import type { CalculatedValue, Readiness, ResolutionState } from '../types/api';
import { formatCalculatedValue, shorten } from '../lib/format';
import { READINESS_LABELS, reasonLabel, STATE_LABELS } from '../lib/labels';

const BUTTON_CLASSES = {
  primary:
    'inline-flex items-center justify-center gap-2 rounded-sm bg-teal px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-teal-dark disabled:cursor-not-allowed disabled:bg-teal-dark disabled:text-white',
  secondary:
    'inline-flex items-center justify-center gap-2 rounded-sm border border-line bg-panel px-4 py-2.5 text-sm font-bold text-ink transition hover:border-teal hover:text-teal disabled:cursor-not-allowed disabled:bg-paper disabled:text-muted',
  quiet:
    'inline-flex items-center justify-center gap-2 rounded-sm px-3 py-2 text-sm font-bold text-teal transition hover:bg-teal/10 disabled:cursor-not-allowed disabled:bg-paper disabled:text-muted',
  danger:
    'inline-flex items-center justify-center gap-2 rounded-sm border border-coral/40 bg-coral/5 px-4 py-2.5 text-sm font-bold text-coral transition hover:bg-coral/10 disabled:cursor-not-allowed disabled:bg-paper disabled:text-muted',
} as const;

const READINESS_CLASSES: Record<Readiness, string> = {
  BLOCKED: 'border-coral/30 bg-coral/10 text-coral',
  READY: 'border-sage/30 bg-sage/10 text-sage',
  READY_WITH_EXCEPTIONS: 'border-amber/30 bg-amber/10 text-amber',
};

const STATE_CLASSES: Record<ResolutionState, string> = {
  auto_cleared: 'border-sage/30 bg-sage/10 text-sage',
  cleared_with_explanation: 'border-teal/30 bg-teal/10 text-teal',
  pending_within_sla: 'border-amber/30 bg-amber/10 text-amber',
  needs_review: 'border-amber/30 bg-amber/10 text-amber',
  critical_exception: 'border-coral/30 bg-coral/10 text-coral',
  excluded: 'border-line bg-paper text-muted',
};

const EVIDENCE_CLASSES = {
  verified: 'border-sage/30 bg-sage/10 text-sage',
  proposed: 'border-amber/30 bg-amber/10 text-amber',
  rejected: 'border-coral/30 bg-coral/10 text-coral',
} as const;

export function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof BUTTON_CLASSES;
}) {
  return (
    <button className={`${BUTTON_CLASSES[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function CopyValue({
  value,
  label = 'Copy value',
}: {
  value: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }
  return (
    <button
      className="inline-flex max-w-full items-center gap-1 rounded border border-line bg-panel px-2 py-1 text-left text-xs text-ink hover:border-teal hover:text-teal"
      title={`${label}: ${value}`}
      aria-label={`${label}: ${value}`}
      onClick={() => void copy()}
      type="button"
    >
      <span className="truncate font-mono">{shorten(value)}</span>
      {copied ? (
        <Check size={14} aria-hidden="true" />
      ) : (
        <Copy size={14} aria-hidden="true" />
      )}
    </button>
  );
}

export function CopyList({
  values,
  label = 'Copy source record',
}: {
  values: string[];
  label?: string;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {values.length ? (
        values.map((value) => (
          <CopyValue key={value} value={value} label={`${label} ${value}`} />
        ))
      ) : (
        <span className="text-sm text-muted">None cited</span>
      )}
    </div>
  );
}

export function CalculatedValues({ values }: { values: CalculatedValue[] }) {
  return values.length ? (
    <dl className="grid gap-2 sm:grid-cols-2">
      {values.map((value) => {
        try {
          return (
            <div key={value.name} className="rounded border border-line bg-paper p-2">
              <dt className="font-mono text-[11px] text-muted">{value.name}</dt>
              <dd className="mt-1 break-all font-mono text-sm font-bold text-ink">
                {formatCalculatedValue(value.name, value.value)}
              </dd>
            </div>
          );
        } catch (error) {
          return (
            <div
              key={value.name}
              className="rounded border border-coral/40 bg-coral/5 p-2"
              role="alert"
            >
              <dt className="font-mono text-[11px] text-coral">{value.name}</dt>
              <dd className="mt-1 break-all font-mono text-sm font-bold text-coral">
                Invalid monetary value: {value.value}
                <span className="sr-only">
                  {' '}
                  {error instanceof Error ? error.message : ''}
                </span>
              </dd>
            </div>
          );
        }
      })}
    </dl>
  ) : null;
}

export function ReadinessBanner({
  readiness,
  counts,
}: {
  readiness: Readiness;
  counts?: string;
}) {
  const Icon =
    readiness === 'BLOCKED'
      ? CircleAlert
      : readiness === 'READY'
        ? ShieldCheck
        : AlertTriangle;
  return (
    <div
      className={`flex items-start gap-3 border p-4 ${READINESS_CLASSES[readiness]}`}
      role="status"
    >
      <Icon size={26} aria-hidden="true" />
      <div>
        <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.16em]">
          Close readiness
        </p>
        <strong className="block text-lg">{READINESS_LABELS[readiness]}</strong>
        {counts && <span className="text-sm">{counts}</span>}
      </div>
    </div>
  );
}

export function StateBadge({ state }: { state: ResolutionState }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-bold ${STATE_CLASSES[state]}`}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATE_LABELS[state]} <span className="sr-only">({state})</span>
    </span>
  );
}

export function EvidenceBadge({
  status,
}: {
  status: 'verified' | 'proposed' | 'rejected';
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-bold ${EVIDENCE_CLASSES[status]}`}
    >
      {status === 'verified' ? (
        <ShieldCheck size={13} aria-hidden="true" />
      ) : (
        <Info size={13} aria-hidden="true" />
      )}
      {status}
    </span>
  );
}

export function ReasonCodes({ codes }: { codes: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {codes.length ? (
        codes.map((code) => (
          <span
            className="rounded border border-line bg-paper px-2 py-1 text-xs text-muted"
            key={code}
            title={code}
          >
            {reasonLabel(code)} <span className="font-mono">{code}</span>
          </span>
        ))
      ) : (
        <span className="text-sm text-muted">No reason codes</span>
      )}
    </div>
  );
}

export function Loading({ label = 'Loading evidence' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 p-8 text-sm text-muted" role="status">
      <LoaderCircle className="animate-spin" size={18} aria-hidden="true" />
      {label}
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 border border-line bg-panel p-6">
      <Info size={22} className="mt-0.5 shrink-0 text-teal" aria-hidden="true" />
      <div>
        <h3 className="font-serif text-xl">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-muted">{children}</p>
      </div>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div
      className="flex items-start gap-3 border border-coral/40 bg-coral/5 p-6"
      role="alert"
    >
      <AlertTriangle
        size={22}
        className="mt-0.5 shrink-0 text-coral"
        aria-hidden="true"
      />
      <div>
        <h3 className="font-serif text-xl text-coral">Evidence unavailable</h3>
        <p className="mt-1 text-sm leading-6 text-ink">{error.message}</p>
        {onRetry && (
          <Button className="mt-4" variant="secondary" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    </div>
  );
}

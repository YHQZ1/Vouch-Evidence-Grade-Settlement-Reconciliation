import { BrainCircuit, ClipboardCheck, Download, ShieldAlert } from 'lucide-react';
import { useState } from 'react';
import type { AgentRun, SettlementResult } from '../../types/api';
import { CopyList, EmptyState, ErrorState, Loading } from '../../components/ui';
import { downloadExport } from '../../lib/api';
import {
  useEffectiveReview,
  useInvestigationEligibility,
  useInvestigations,
  useRunInvestigation,
} from '../../lib/queries';

type Props = { batchId: string; settlementId: string; settlement: SettlementResult };

export function InvestigationPanel({ batchId, settlementId, settlement }: Props) {
  const runs = useInvestigations(batchId, settlementId);
  const eligibility = useInvestigationEligibility(batchId, settlementId);
  const effective = useEffectiveReview(batchId, settlementId);
  const mutation = useRunInvestigation(batchId, settlementId);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  if (settlement.state !== 'needs_review') return null;
  const latest = runs.data?.items.at(-1);
  const accepted = effective.data?.review.accepted_decision;
  const providerDisabled = eligibility.data?.provider_available === false;
  const serverEligible = eligibility.data?.eligible === true && !providerDisabled;
  const disabled = providerDisabled || latest?.failure_reason_code === 'AI_DISABLED';
  const refreshing = runs.isFetching || eligibility.isFetching || effective.isFetching;
  return (
    <section
      className="border border-teal/30 bg-teal/5 p-5 sm:p-7"
      aria-labelledby="investigation-title"
    >
      <PanelTitle
        eyebrow="Bounded investigation"
        title="Investigate ambiguous evidence"
      >
        <BrainCircuit size={21} aria-hidden="true" />
      </PanelTitle>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
        {serverEligible ? (
          <>
            The server marks this settlement eligible for a bounded local investigation.
            The model can inspect only this case’s allowlisted evidence and can propose
            or abstain; deterministic verification owns every effective state.
          </>
        ) : (
          <>
            The server has not marked this settlement eligible. No investigation action
            is available.
          </>
        )}
      </p>
      <div className="mt-5 grid gap-3 text-sm sm:grid-cols-3">
        <Info label="Provider mode" value="Disabled by default / local Ollama only" />
        <Info label="Limits" value="6 steps · 15 seconds · 20 records" />
        <Info label="Authority" value="Verifier only · never auto_clears" />
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        <button
          className="inline-flex items-center gap-2 bg-teal px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          onClick={() => mutation.mutate()}
          disabled={
            !serverEligible ||
            accepted != null ||
            disabled ||
            mutation.isPending ||
            refreshing
          }
        >
          <BrainCircuit size={16} aria-hidden="true" />{' '}
          {mutation.isPending ? 'Investigating…' : 'Investigate ambiguous evidence'}
        </button>
        {!serverEligible && eligibility.data?.explanation && (
          <p className="self-center text-sm text-muted">
            {eligibility.data.explanation}
          </p>
        )}
        {disabled && (
          <p className="self-center text-sm text-muted">
            AI is disabled or unavailable; this panel is read-only.
          </p>
        )}
        <button
          className="inline-flex items-center gap-2 border border-line px-4 py-2 text-sm font-bold text-ink hover:border-teal"
          type="button"
          disabled={exporting}
          onClick={() => {
            setExportError(null);
            setExporting(true);
            void downloadExport(batchId, 'investigations')
              .catch((error: unknown) => {
                setExportError(
                  error instanceof Error ? error.message : 'Export failed safely.',
                );
              })
              .finally(() => setExporting(false));
          }}
        >
          <Download size={16} aria-hidden="true" />{' '}
          {exporting ? 'Exporting…' : 'Export investigations'}
        </button>
      </div>
      {exportError && (
        <p
          className="mt-4 border border-coral/30 bg-coral/5 p-3 text-sm text-coral"
          role="alert"
        >
          {exportError} Retry the export when the API is available.
        </p>
      )}
      {mutation.isError && (
        <p
          className="mt-4 border border-coral/30 bg-coral/5 p-3 text-sm text-coral"
          role="alert"
        >
          {mutation.error instanceof Error
            ? mutation.error.message
            : 'The investigation could not be started safely.'}
        </p>
      )}
      {eligibility.isError && (
        <div className="mt-4">
          <ErrorState
            error={eligibility.error}
            onRetry={() => void eligibility.refetch()}
          />
        </div>
      )}
      {effective.isError && (
        <div className="mt-4">
          <ErrorState
            error={effective.error}
            onRetry={() => void effective.refetch()}
          />
        </div>
      )}
      {runs.isLoading ? (
        <div className="mt-5">
          <Loading />
        </div>
      ) : runs.isError ? (
        <div className="mt-5">
          <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />
        </div>
      ) : runs.data?.items.length ? (
        <div className="mt-6 space-y-3">
          <h3 className="flex items-center gap-2 text-sm font-bold">
            <ClipboardCheck size={16} className="text-teal" /> Append-only run history
          </h3>
          {runs.data.items.map((run) => (
            <RunCard key={run.run_id} run={run} />
          ))}
        </div>
      ) : (
        <div className="mt-5">
          <EmptyState title="No investigation runs yet">
            The deterministic result remains the only effective state until an explicit
            investigation is invoked.
          </EmptyState>
        </div>
      )}
      {accepted && (
        <div className="mt-5 border border-sage/30 bg-sage/5 p-4 text-sm">
          <strong>Verifier accepted.</strong> Prior state{' '}
          <code>{effective.data?.review.base_state}</code> remains recorded; effective
          state is <code>{effective.data?.review.effective_state}</code>. Base and
          post-investigation close assessments remain separate.
        </div>
      )}
      {!accepted && latest?.status === 'rejected' && (
        <div className="mt-5 flex gap-3 border border-coral/30 bg-coral/5 p-4 text-sm">
          <ShieldAlert size={18} className="mt-0.5 shrink-0 text-coral" />
          <span>
            <strong>Hypothesis rejected.</strong> This case remains{' '}
            <code>needs_review</code>; no effective decision was created.
          </span>
        </div>
      )}
    </section>
  );
}

function RunCard({ run }: { run: AgentRun }) {
  return (
    <details className="border border-line bg-paper">
      <summary className="cursor-pointer list-none p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <strong className="capitalize">{run.status}</strong>
          <span className="font-mono text-xs text-muted">{run.run_id}</span>
        </div>
        <p className="mt-2 text-xs text-muted">
          {run.model_mode} · {run.configured_model_identifier ?? 'no model'} ·{' '}
          {run.steps.length} steps · {run.total_duration_ms} ms
        </p>
      </summary>
      <div className="space-y-4 border-t border-line p-4">
        <Meta
          label="Versions"
          value={`${run.prompt_version} · ${run.tool_version} · ${run.verifier_version}`}
        />
        <Meta label="Failure / abstention" value={run.failure_reason_code ?? 'none'} />
        <div>
          <p className="mb-2 text-xs text-muted">Source fingerprints</p>
          <CopyList values={run.source_fingerprints} label="Copy fingerprint" />
        </div>
        <div>
          <p className="mb-2 text-xs text-muted">Read-only tool trace</p>
          {run.steps.length ? (
            <ol className="space-y-2">
              {run.steps.map((step) => (
                <li
                  className="border-l-2 border-line pl-3 text-sm"
                  key={step.sequence_number}
                >
                  <strong>
                    Step {step.sequence_number}: {step.action_type}
                  </strong>
                  {step.request && (
                    <p className="font-mono text-xs text-muted">
                      {step.request.tool_name}
                    </p>
                  )}
                  {step.tool_result?.source_record_ids.length ? (
                    <CopyList
                      values={step.tool_result.source_record_ids}
                      label="Copy cited source ID"
                    />
                  ) : null}
                  {step.failure_reason_code && (
                    <p className="text-xs text-coral">{step.failure_reason_code}</p>
                  )}
                </li>
              ))}
            </ol>
          ) : (
            <span className="text-sm text-muted">No tool calls retained.</span>
          )}
        </div>
        {run.hypothesis && (
          <div className="border border-line bg-white p-3 text-sm">
            <strong>Structured hypothesis</strong>
            <p className="mt-2">{run.hypothesis.evidence_claim}</p>
            <p className="mt-2 font-mono text-xs">
              Candidate: {run.hypothesis.proposed_bank_source_record_id}
            </p>
            <CopyList
              values={run.hypothesis.cited_source_record_ids}
              label="Copy cited source ID"
            />
          </div>
        )}
        {run.verification && (
          <div
            className={`p-3 text-sm ${run.verification.accepted ? 'border border-sage/30 bg-sage/5' : 'border border-coral/30 bg-coral/5'}`}
          >
            <strong>
              {run.verification.accepted
                ? 'Accepted by deterministic verifier'
                : 'Rejected by deterministic verifier'}
            </strong>
            <p className="mt-1">{run.verification.explanation}</p>
            <p className="mt-2 font-mono text-xs">
              {run.verification.reason_codes.join(', ')}
            </p>
          </div>
        )}
      </div>
    </details>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-teal/20 bg-white p-3">
      <span className="block text-[11px] font-bold uppercase tracking-[0.12em] text-muted">
        {label}
      </span>
      <span className="mt-1 block text-sm">{value}</span>
    </div>
  );
}
function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-muted">{label}</span>
      <p className="mt-1 font-mono text-xs">{value}</p>
    </div>
  );
}
function PanelTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
          {eyebrow}
        </p>
        <h2 className="font-serif text-2xl" id="investigation-title">
          {title}
        </h2>
      </div>
      <span className="text-teal">{children}</span>
    </div>
  );
}

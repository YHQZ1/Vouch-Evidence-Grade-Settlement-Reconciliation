import { useParams } from 'react-router-dom';
import type { ResolutionState } from '../../types/api';
import { useResult } from '../../lib/queries';
import { resolveBatchId } from '../../lib/batch-ref';
import { formatDate, formatSubunits } from '../../lib/format';
import { READINESS_LABELS } from '../../lib/labels';
import { ErrorState, Loading, ReadinessBanner, StateBadge } from '../../components/ui';

const METRIC_TITLE_CLASSES = {
  verified: 'text-sage',
  explained: 'text-teal',
  pending: 'text-amber',
  unresolved: 'text-coral',
  total: 'text-muted',
} as const;

export function OverviewPage() {
  const { batchId: batchRef } = useParams();
  const batchId = resolveBatchId(batchRef);
  const query = useResult(batchId);
  if (query.isLoading) return <Loading />;
  if (query.isError || !query.data)
    return (
      <ErrorState
        error={query.error ?? new Error('The completed result is unavailable.')}
        onRetry={() => void query.refetch()}
      />
    );
  const result = query.data;
  const readiness = result.close_readiness;
  const stateCounts = result.settlements.reduce<
    Partial<Record<ResolutionState, number>>
  >((counts, item) => {
    counts[item.state] = (counts[item.state] ?? 0) + 1;
    return counts;
  }, {});
  const blocking = result.exceptions.filter((item) => item.blocking).length;
  const permitted = result.exceptions.filter((item) => !item.blocking).length;
  const totalSettlements = result.settlements.length;
  const metrics = [
    ['Verified value', readiness.verified_value_subunits, 'verified'],
    ['Explained value', readiness.explained_value_subunits, 'explained'],
    ['Pending value', readiness.pending_value_subunits, 'pending'],
    ['Unresolved value', readiness.unresolved_value_subunits, 'unresolved'],
    ['Total absolute value', readiness.batch_total_abs_value_subunits, 'total'],
  ] as const;
  return (
    <div id="main-content" className="space-y-5">
      <div className="grid gap-8 border-b border-line pb-8 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.42fr)] lg:items-end lg:gap-12">
        <PageHeader
          eyebrow="Close readiness"
          title="Can this batch close?"
          description={`A deterministic assessment of ${result.settlements.length} settlements at ${formatDate(result.evaluation_clock)}.`}
        />
        <ReadinessBanner
          readiness={readiness.readiness}
          counts={`${blocking} blocking · ${permitted} permitted exceptions`}
        />
      </div>
      <div className="grid gap-y-8 sm:grid-cols-2 xl:grid-cols-5 xl:divide-x xl:divide-line">
        {metrics.map(([label, value, kind]) => (
          <div
            className="flex min-w-0 flex-col px-5 py-1 first:pl-0 xl:last:pr-0"
            key={label}
          >
            <span
              className={`text-xs font-bold uppercase tracking-[0.1em] ${METRIC_TITLE_CLASSES[kind]}`}
            >
              {label}
            </span>
            <strong className="mt-3 block truncate font-mono text-2xl font-medium leading-none tracking-[-0.04em]">
              {formatSubunits(value)}
            </strong>
          </div>
        ))}
      </div>
      <section className="grid gap-8 border-t border-line pt-8 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="py-1 sm:py-2">
          <PanelHeading eyebrow="What the controls say" title="Resolution coverage" />
          <p className="mt-3 max-w-xl text-sm leading-6 text-muted">
            Each bar shows how settlements resolved after gateway, bank and ledger
            evidence were compared. A longer bar means more settlements share that
            outcome.
          </p>
          <div className="mt-6 space-y-5">
            {Object.entries(stateCounts)
              .sort()
              .map(([state, count]) => (
                <div key={state}>
                  <div className="flex items-center justify-between gap-3">
                    <StateBadge state={state as ResolutionState} />
                    <span className="font-mono text-sm text-muted">
                      {count} / {totalSettlements} ·{' '}
                      {Math.round((count / Math.max(1, totalSettlements)) * 100)}%
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden bg-paper">
                    <div
                      className="h-full bg-teal"
                      style={{
                        width: `${(count / Math.max(1, totalSettlements)) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>
          <div className="mt-7 border-t border-line pt-5 text-sm">
            <div>
              <strong>
                {readiness.readiness === 'BLOCKED'
                  ? 'Resolve every blocking exception before close.'
                  : readiness.readiness === 'READY'
                    ? 'No blocking control is open.'
                    : 'Review the permitted exceptions in the proof packet.'}
              </strong>
              <p className="mt-1 leading-6 text-muted">
                {READINESS_LABELS[readiness.readiness]} is derived by the versioned
                close policy; Vouch does not offer a client-side override.
              </p>
            </div>
          </div>
        </div>
        <div className="py-1 sm:py-2">
          <PanelHeading eyebrow="Provenance" title="Inputs and rules" />
          <p className="mt-3 text-sm leading-6 text-muted">
            The run is reproducible because the clock, schema and close policy are fixed
            alongside the source files.
          </p>
          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted">Evaluation clock</dt>
              <dd className="mt-1 font-mono text-xs">{result.evaluation_clock}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Schema / rule</dt>
              <dd className="mt-1 font-mono text-xs">
                {result.schema_version} / {result.rule_version}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs text-muted">Policy</dt>
              <dd className="mt-1 font-mono text-xs">{result.policy_version}</dd>
            </div>
          </dl>
        </div>
      </section>
      <section className="border-t border-line pt-8" aria-labelledby="intake-title">
        <PanelHeading eyebrow="Source intake" title="Every source row accounted for" />
        <p id="intake-title" className="mt-3 max-w-2xl text-sm leading-6 text-muted">
          Accepted rows are available to the reconciliation controls; rejected rows stay
          visible so the evidence trail is complete.
        </p>
        <div className="mt-5 divide-y divide-line border-y border-line">
          {result.ingestion.map((item) => (
            <div
              className="grid gap-2 py-4 sm:grid-cols-[minmax(180px,1.2fr)_minmax(160px,1fr)_minmax(120px,auto)] sm:items-center"
              key={item.source_kind}
            >
              <strong>{item.source_name}</strong>
              <span className="font-mono text-sm text-muted">
                {item.accepted_row_count} / {item.row_count} passed
              </span>
              <span
                className={`text-sm ${item.rejected_row_count ? 'text-coral' : 'text-sage'}`}
              >
                {item.rejected_row_count ? `${item.rejected_row_count} rejected` : '—'}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
          {eyebrow}
        </p>
        <h1 className="font-sans font-light tracking-tight text-4xl sm:text-5xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">{description}</p>
      </div>
      {action}
    </div>
  );
}
function PanelHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
          {eyebrow}
        </p>
        <h2 className="font-sans font-light tracking-tight text-2xl">{title}</h2>
      </div>
      {children ? <span className="text-teal">{children}</span> : null}
    </div>
  );
}

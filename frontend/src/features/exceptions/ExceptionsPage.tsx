import { ArrowRight, CircleAlert, Filter } from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { AuditDrawer } from '../../components/AuditDrawer';
import { CopyList, EmptyState, ErrorState, Loading } from '../../components/ui';
import { formatSubunits } from '../../lib/format';
import { reasonLabel } from '../../lib/labels';
import { useExceptions } from '../../lib/queries';

export function ExceptionsPage() {
  const { batchId } = useParams();
  const [params, setParams] = useSearchParams();
  const query = useExceptions(batchId);
  if (query.isLoading) return <Loading />;
  if (query.isError || !query.data)
    return (
      <ErrorState
        error={query.error ?? new Error('Exception queue unavailable.')}
        onRetry={() => void query.refetch()}
      />
    );
  const material = params.get('material') ?? '';
  const blocking = params.get('blocking') ?? '';
  const reason = params.get('reason') ?? '';
  const settlement = params.get('settlement') ?? '';
  const reasons = [...new Set(query.data.items.map((item) => item.reason_code))].sort();
  const items = query.data.items
    .filter(
      (item) =>
        (!material || String(item.material) === material) &&
        (!blocking || String(item.blocking) === blocking) &&
        (!reason || item.reason_code === reason) &&
        (!settlement || item.settlement_id?.includes(settlement)),
    )
    .sort(
      (a, b) =>
        Number(b.material) - Number(a.material) ||
        Number(b.blocking) - Number(a.blocking) ||
        Math.abs(b.value_subunits) - Math.abs(a.value_subunits) ||
        a.reason_code.localeCompare(b.reason_code) ||
        a.exception_id.localeCompare(b.exception_id),
    );
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    value ? next.set(key, value) : next.delete(key);
    setParams(next);
  };
  return (
    <div id="main-content" className="space-y-5">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
            Control queue / {query.data.total} total
          </p>
          <h1 className="font-serif text-4xl sm:text-5xl">Exceptions</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
            Every surfaced exception is reachable here. The queue ranks material,
            blocking, absolute value, reason code, then exception ID.
          </p>
        </div>
        <div className="flex items-center gap-2 border border-coral/30 bg-coral/5 px-3 py-2 text-sm text-coral">
          <CircleAlert size={18} aria-hidden="true" />
          <strong>
            {items.filter((item) => item.material).length} material visible
          </strong>
        </div>
      </div>
      <div className="flex flex-col gap-3 border border-line bg-panel p-4 lg:flex-row lg:items-end">
        <Filter size={17} className="mb-3 text-teal lg:mb-0" aria-hidden="true" />
        <FilterSelect
          label="Material"
          value={material}
          onChange={(value) => setFilter('material', value)}
          options={[
            ['', 'All'],
            ['true', 'Material'],
            ['false', 'Non-material'],
          ]}
        />
        <FilterSelect
          label="Blocking"
          value={blocking}
          onChange={(value) => setFilter('blocking', value)}
          options={[
            ['', 'All'],
            ['true', 'Blocking'],
            ['false', 'Permitted'],
          ]}
        />
        <FilterSelect
          label="Reason"
          value={reason}
          onChange={(value) => setFilter('reason', value)}
          options={[
            ['', 'All reason codes'],
            ...reasons.map((code) => [code, reasonLabel(code)] as const),
          ]}
        />
        <label className="text-xs font-bold uppercase tracking-[0.1em] text-muted">
          Settlement
          <input
            className="mt-2 block rounded-sm border border-line bg-paper px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-ink"
            value={settlement}
            onChange={(event) => setFilter('settlement', event.target.value)}
            placeholder="set_…"
          />
        </label>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No exceptions match these filters">
          The queue is empty for the current filter state. The API still owns the
          canonical exception total.
        </EmptyState>
      ) : (
        <div className="space-y-3">
          {items.map((item, index) => (
            <article
              className={`grid gap-4 border bg-panel p-4 sm:grid-cols-[auto_1fr_auto] sm:p-5 ${item.blocking ? 'border-coral/40' : 'border-line'}`}
              key={item.exception_id}
            >
              <div className="font-mono text-xs text-muted">
                {String(index + 1).padStart(2, '0')}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full border px-2 py-1 text-xs font-bold ${item.blocking ? 'border-coral/30 bg-coral/10 text-coral' : 'border-amber/30 bg-amber/10 text-amber'}`}
                  >
                    {item.material ? 'Material' : 'Non-material'} ·{' '}
                    {item.blocking ? 'Blocking' : 'Permitted'}
                  </span>
                  <span className="font-mono text-xs text-muted">
                    {item.reason_code}
                  </span>
                </div>
                <h2 className="mt-3 font-serif text-2xl">
                  {reasonLabel(item.reason_code)}
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted">{item.explanation}</p>
                <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
                  <span>
                    Value{' '}
                    <strong className="font-mono">
                      {formatSubunits(item.value_subunits)}
                    </strong>
                  </span>
                  <span>
                    Settlement{' '}
                    <Link
                      className="font-mono text-teal hover:underline"
                      to={`/batches/${batchId}/settlements/${encodeURIComponent(item.settlement_id ?? '')}`}
                    >
                      {item.settlement_id ?? 'Batch-level'}
                    </Link>
                  </span>
                  <span>{item.source_record_ids.length} cited source records</span>
                </div>
                <div className="mt-4">
                  <p className="mb-2 text-xs font-bold uppercase tracking-[0.1em] text-muted">
                    Cited source IDs — each copyable
                  </p>
                  <CopyList values={item.source_record_ids} />
                </div>
              </div>
              <div className="flex flex-wrap items-start gap-2 sm:flex-col sm:items-stretch">
                <AuditDrawer
                  batchId={batchId!}
                  settlementId={item.settlement_id ?? undefined}
                  trigger={
                    <>
                      <CircleAlert size={15} /> Audit trail
                    </>
                  }
                />
                {item.settlement_id && (
                  <Link
                    className="inline-flex items-center justify-center gap-2 rounded-sm border border-line px-3 py-2 text-sm font-bold text-teal hover:border-teal"
                    to={`/batches/${batchId}/settlements/${encodeURIComponent(item.settlement_id)}`}
                  >
                    Settlement <ArrowRight size={15} />
                  </Link>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly (readonly [string, string])[];
}) {
  return (
    <label className="text-xs font-bold uppercase tracking-[0.1em] text-muted">
      {label}
      <select
        className="mt-2 block rounded-sm border border-line bg-paper px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-ink"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map(([option, text]) => (
          <option key={option} value={option}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

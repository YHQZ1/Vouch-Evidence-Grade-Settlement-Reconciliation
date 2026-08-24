import { ChevronDown, Search } from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useSettlements } from '../../lib/queries';
import { resolveBatchId } from '../../lib/batch-ref';
import { formatDate, formatSubunits } from '../../lib/format';
import { reasonLabel, STATE_LABELS } from '../../lib/labels';
import { EmptyState, ErrorState, Loading, StateBadge } from '../../components/ui';

export function SettlementsPage() {
  const { batchId: batchRef } = useParams();
  const batchId = resolveBatchId(batchRef);
  const [params, setParams] = useSearchParams();
  const query = useSettlements(batchId);
  if (query.isLoading) return <Loading />;
  if (query.isError || !query.data)
    return (
      <ErrorState
        error={query.error ?? new Error('Settlements unavailable.')}
        onRetry={() => void query.refetch()}
      />
    );
  const search = params.get('q') ?? '';
  const state = params.get('state') ?? '';
  const exception = params.get('exception') ?? '';
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    value ? next.set(key, value) : next.delete(key);
    setParams(next);
  };
  const items = query.data.items.filter((item) => {
    const needle = search.trim().toLowerCase();
    const compactNeedle = needle.replace(/[\s,₹]/g, '');
    const searchableText = [
      item.aggregate.settlement_id,
      item.aggregate.aggregate_id,
      item.aggregate.balance_account_id ?? '',
      ...item.aggregate.normalized_utrs,
      ...item.aggregate.member_source_record_ids,
      ...item.aggregate.member_entity_ids,
      ...item.reason_codes,
      ...item.reason_codes.map(reasonLabel),
      ...item.exceptions.flatMap((exception) => [
        exception.reason_code,
        reasonLabel(exception.reason_code),
      ]),
      STATE_LABELS[item.state],
      item.state,
      formatSubunits(item.aggregate.signed_net.subunits),
    ]
      .join(' ')
      .toLowerCase();
    const compactSearchableText = searchableText.replace(/[\s,₹]/g, '');
    const matchesSearch =
      !needle ||
      searchableText.includes(needle) ||
      compactSearchableText.includes(compactNeedle);
    const hasException = item.exceptions.length > 0;
    return (
      matchesSearch &&
      (!state || item.state === state) &&
      (!exception || (exception === 'yes' ? hasException : !hasException))
    );
  });
  return (
    <div id="main-content" className="space-y-5">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal">
            Evidence review / {query.data.total} total
          </p>
          <h1 className="font-sans font-light tracking-tight text-4xl sm:text-5xl">
            Settlements
          </h1>
        </div>
      </div>
      <div className="flex flex-col gap-3 border border-line bg-panel p-4 lg:flex-row lg:items-end">
        <label className="min-w-0 flex-1 text-xs font-bold uppercase tracking-[0.1em] text-muted">
          <span className="sr-only">Search settlements</span>
          <span className="relative block">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
              size={17}
              aria-hidden="true"
            />
            <input
              className="w-full rounded-sm border border-line bg-paper py-2.5 pl-10 pr-3 text-sm font-normal normal-case tracking-normal text-ink"
              value={search}
              onChange={(event) => setFilter('q', event.target.value)}
              placeholder="Search settlement or balance account"
            />
          </span>
        </label>
        <FilterSelect
          label="State"
          value={state}
          onChange={(value) => setFilter('state', value)}
          options={[
            ['', 'All states'],
            ['auto_cleared', 'Auto-cleared'],
            ['cleared_with_explanation', 'Cleared with explanation'],
            ['pending_within_sla', 'Pending within SLA'],
            ['needs_review', 'Needs review'],
            ['critical_exception', 'Critical exception'],
            ['excluded', 'Excluded'],
          ]}
        />
        <FilterSelect
          label="Exceptions"
          value={exception}
          onChange={(value) => setFilter('exception', value)}
          options={[
            ['', 'Exceptions'],
            ['yes', 'With exceptions'],
            ['no', 'No exceptions'],
          ]}
        />
      </div>
      {items.length === 0 ? (
        <EmptyState title="No settlements match these filters">
          The API returned {query.data.total} settlements, but none match the current
          URL filters.
        </EmptyState>
      ) : (
        <div className="overflow-x-auto border border-line bg-panel">
          <table className="w-full min-w-[800px] border-collapse text-left text-sm">
            <caption className="sr-only">Complete settlement evidence list</caption>
            <thead className="bg-paper text-xs uppercase tracking-[0.1em] text-muted">
              <tr>
                {[
                  'Settlement',
                  'Settled at',
                  'Signed net',
                  'State',
                  'Reasons',
                  'Evidence checks',
                  'Unresolved',
                ].map((heading) => (
                  <th
                    className="border-b border-line px-4 py-3 font-bold"
                    key={heading}
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  className="border-b border-line last:border-0 hover:bg-paper/70"
                  key={item.aggregate.settlement_id}
                >
                  <td className="px-4 py-4">
                    <Link
                      className="font-mono text-xs font-medium text-teal hover:underline"
                      to={`/batches/${batchRef}/settlements/${encodeURIComponent(item.aggregate.settlement_id)}`}
                    >
                      {item.aggregate.settlement_id}
                    </Link>
                    <small className="mt-1 block text-muted">
                      {item.aggregate.balance_account_id ?? '—'}
                    </small>
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 text-sm text-muted">
                    {formatDate(item.aggregate.latest_settled_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 font-mono font-medium">
                    {formatSubunits(item.aggregate.signed_net.subunits)}
                  </td>
                  <td className="px-4 py-4">
                    <StateBadge state={item.state} />
                  </td>
                  <td className="max-w-64 px-4 py-4">
                    <div className="flex flex-wrap gap-1">
                      {item.reason_codes.map((code) => (
                        <span
                          className="rounded border border-line px-1.5 py-0.5 text-xs text-muted"
                          key={code}
                          title={code}
                        >
                          {reasonLabel(code)}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-xs">
                    <span
                      className={
                        item.accepted_evidence_links.some(
                          (link) => link.relationship_type === 'settlement_to_bank',
                        )
                          ? 'block text-sage'
                          : 'block text-coral'
                      }
                    >
                      {item.accepted_evidence_links.some(
                        (link) => link.relationship_type === 'settlement_to_bank',
                      )
                        ? 'Bank verified'
                        : 'Bank open'}
                    </span>
                    <span
                      className={
                        item.accounting_control?.complete_evidence
                          ? 'block text-sage'
                          : 'block text-coral'
                      }
                    >
                      {item.accounting_control?.complete_evidence
                        ? 'Ledger complete'
                        : 'Ledger open'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 font-mono">
                    {formatSubunits(item.unresolved_value_subunits)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
    <label className="relative block w-44">
      <span className="sr-only">{label}</span>
      <select
        className="block h-11 w-full appearance-none rounded-sm border border-line bg-paper px-3 pr-10 text-sm font-normal text-ink"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map(([option, text]) => (
          <option key={option} value={option}>
            {text}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted"
        size={16}
        aria-hidden="true"
      />
    </label>
  );
}

import {
  FileWarning,
  LayoutDashboard,
  Menu,
  PanelLeftClose,
  ScrollText,
  ShieldCheck,
  Download,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom';
import { ApiRequestError, downloadExport } from '../lib/api';
import { useBatch } from '../lib/queries';
import { resolveBatchId } from '../lib/batch-ref';
import { Button, ErrorState, Loading, VouchMark } from './ui';

export function Layout() {
  const { batchId: batchRef } = useParams();
  const batchId = resolveBatchId(batchRef);
  const navigate = useNavigate();
  const { data: batch, isLoading, isError, error, refetch } = useBatch(batchId);
  const [open, setOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(
    () =>
      typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches,
  );
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const sidebarId = 'batch-review-sidebar';
  useEffect(() => {
    const media = window.matchMedia('(min-width: 1024px)');
    const update = () => setIsDesktop(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  const sidebarClosed = !isDesktop && !open;
  useEffect(() => {
    if (!open || isDesktop) return;
    const frame = window.requestAnimationFrame(() => {
      sidebarRef.current?.querySelector<HTMLElement>('[data-nav-link]')?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [open, isDesktop]);
  function closeNavigation() {
    setOpen(false);
    if (!isDesktop) window.setTimeout(() => menuButtonRef.current?.focus(), 0);
  }
  if (isLoading)
    return (
      <ShellState>
        <Loading />
      </ShellState>
    );
  if (isError || !batch)
    return (
      <ShellState>
        <ErrorState
          error={
            error ?? new Error('This batch no longer exists in the local API process.')
          }
          onRetry={() => void refetch()}
        />
        <Button variant="secondary" onClick={() => navigate('/')}>
          Return to batch setup
        </Button>
      </ShellState>
    );
  const isReview = batch.status === 'completed';
  const nav = [
    { to: `/batches/${batchRef}/overview`, label: 'Overview', icon: LayoutDashboard },
    { to: `/batches/${batchRef}/settlements`, label: 'Settlements', icon: ScrollText },
    { to: `/batches/${batchRef}/exceptions`, label: 'Exceptions', icon: FileWarning },
  ];
  return (
    <div className="min-h-screen bg-paper text-ink">
      <SkipLink />
      <header className="sticky top-0 z-30 flex min-h-16 items-center gap-3 border-b border-line bg-panel/95 px-4  sm:px-6">
        <button
          ref={menuButtonRef}
          className="rounded-sm p-2 text-teal hover:bg-teal/10 lg:hidden"
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={open}
          aria-controls={sidebarId}
          onClick={() => (open ? closeNavigation() : setOpen(true))}
        >
          {open ? <PanelLeftClose /> : <Menu />}
        </button>
        <button
          className="flex items-center gap-2 font-sans font-light tracking-tight text-2xl font-bold"
          type="button"
          onClick={() => navigate('/')}
        >
          <VouchMark className="h-8 w-8" />
          <span>Vouch</span>
        </button>
        <div className="ml-auto flex items-center gap-2 text-xs text-muted">
          <span className="hidden md:inline">Evidence Review Workspace</span>
        </div>
      </header>
      <div className="flex min-h-[calc(100vh-4rem)]">
        <aside
          id={sidebarId}
          ref={sidebarRef}
          aria-hidden={sidebarClosed}
          {...(sidebarClosed ? { inert: '' } : {})}
          className={`fixed inset-y-16 left-0 z-20 w-72 border-r border-line bg-panel p-5 transition-transform lg:sticky lg:top-16 lg:block lg:h-[calc(100vh-4rem)] lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}
        >
          <nav aria-label="Batch review">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted">
              Review workspace
            </p>
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                data-nav-link
                key={to}
                to={to}
                onClick={closeNavigation}
                className={({ isActive }) =>
                  `mb-1 flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm font-bold ${isActive ? 'bg-teal text-white' : 'text-muted hover:bg-paper hover:text-ink'}`
                }
              >
                <Icon size={17} aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-4 border-t border-line pt-5">
            <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.16em] text-muted">
              Exports
            </p>
            <ExportActions batchId={batch.batch_id} enabled={isReview} />
          </div>
        </aside>
        {open && (
          <button
            className="fixed inset-0 z-10 bg-ink/30 lg:hidden"
            type="button"
            aria-label="Close navigation"
            onClick={closeNavigation}
          />
        )}
        <main className="min-w-0 flex-1">
          {!isReview && (
            <div className="mx-4 mt-5 flex items-start gap-2 border border-amber/30 bg-amber/10 p-3 text-sm text-amber sm:mx-7">
              <ShieldCheck size={16} aria-hidden="true" />
              This batch is not yet reviewable. Finish uploads and run deterministic
              reconciliation.
            </div>
          )}
          <div className="mx-auto w-full p-4 sm:p-7">
            <Outlet context={{ batch }} />
          </div>
        </main>
      </div>
    </div>
  );
}

export function ExportActions({
  batchId,
  enabled,
}: {
  batchId: string;
  enabled: boolean;
}) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    kind: 'success' | 'error';
    text: string;
  } | null>(null);
  const [lastArtifact, setLastArtifact] = useState<
    'reconciliation-result' | 'exceptions' | 'audit-events' | null
  >(null);
  const labels = {
    'reconciliation-result': 'Result',
    exceptions: 'Exceptions',
    'audit-events': 'Audit events',
  } as const;
  async function run(
    artifact: 'reconciliation-result' | 'exceptions' | 'audit-events',
  ) {
    if (exporting) return;
    setExporting(artifact);
    setMessage(null);
    setLastArtifact(artifact);
    try {
      const filename = await downloadExport(batchId, artifact);
      setMessage({ kind: 'success', text: `${filename} downloaded.` });
    } catch (caught) {
      setMessage({
        kind: 'error',
        text:
          caught instanceof ApiRequestError
            ? `${caught.code}: ${caught.message}`
            : 'Export failed. Retry when the API is available.',
      });
    } finally {
      setExporting(null);
    }
  }
  return (
    <div className="space-y-2">
      <div className="grid gap-2">
        <button
          className="flex items-center gap-2 rounded-sm border border-line px-3 py-2 text-left text-sm font-bold text-teal hover:border-teal disabled:cursor-not-allowed disabled:bg-paper disabled:text-muted"
          type="button"
          disabled={!enabled || Boolean(exporting)}
          onClick={() => void run('reconciliation-result')}
        >
          <Download size={15} aria-hidden="true" />
          {exporting === 'reconciliation-result'
            ? 'Preparing…'
            : labels['reconciliation-result']}
        </button>
        <button
          className="flex items-center gap-2 rounded-sm border border-line px-3 py-2 text-left text-sm font-bold text-teal hover:border-teal disabled:cursor-not-allowed disabled:bg-paper disabled:text-muted"
          type="button"
          disabled={!enabled || Boolean(exporting)}
          onClick={() => void run('exceptions')}
        >
          <Download size={15} aria-hidden="true" />
          {exporting === 'exceptions' ? 'Preparing…' : labels.exceptions}
        </button>
        <button
          className="flex items-center gap-2 rounded-sm border border-line px-3 py-2 text-left text-sm font-bold text-teal hover:border-teal disabled:cursor-not-allowed disabled:bg-paper disabled:text-muted"
          type="button"
          disabled={!enabled || Boolean(exporting)}
          onClick={() => void run('audit-events')}
        >
          <Download size={15} aria-hidden="true" />
          {exporting === 'audit-events' ? 'Preparing…' : labels['audit-events']}
        </button>
      </div>
      {message && (
        <div
          className={`text-xs leading-5 ${message.kind === 'error' ? 'text-coral' : 'text-sage'}`}
          role={message.kind === 'error' ? 'alert' : 'status'}
          aria-live="polite"
        >
          {message.text}
          {message.kind === 'error' && lastArtifact && (
            <button
              className="ml-1 font-bold underline"
              type="button"
              onClick={() => void run(lastArtifact)}
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ShellState({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SkipLink />
      <main
        id="main-content"
        className="grid min-h-screen place-items-center gap-4 p-6"
      >
        {children}
      </main>
    </>
  );
}
function SkipLink() {
  return (
    <a
      className="fixed left-2 top-2 z-[60] -translate-y-20 rounded bg-ink px-3 py-2 text-sm text-white transition focus:translate-y-0"
      href="#main-content"
    >
      Skip to content
    </a>
  );
}

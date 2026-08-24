import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { BatchSetupPage } from './features/batch/BatchSetupPage';
import { OverviewPage } from './features/overview/OverviewPage';
import { SettlementsPage } from './features/settlements/SettlementsPage';
import { SettlementDetailPage } from './features/settlements/SettlementDetailPage';
import { ExceptionsPage } from './features/exceptions/ExceptionsPage';
import './styles.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
});
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<BatchSetupPage />} />
          <Route path="/batches/:batchId" element={<Layout />}>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<OverviewPage />} />
            <Route path="settlements" element={<SettlementsPage />} />
            <Route
              path="settlements/:settlementId"
              element={<SettlementDetailPage />}
            />
            <Route path="exceptions" element={<ExceptionsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

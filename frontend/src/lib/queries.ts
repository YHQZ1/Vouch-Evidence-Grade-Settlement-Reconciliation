import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api';

export function useBatch(batchId: string | undefined) {
  return useQuery({
    queryKey: ['batch', batchId],
    queryFn: ({ signal }) => api.getBatch(batchId!, signal),
    enabled: Boolean(batchId),
    retry: false,
    staleTime: 2_000,
  });
}
export function useResult(batchId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['result', batchId],
    queryFn: ({ signal }) => api.getResult(batchId!, signal),
    enabled: Boolean(batchId) && enabled,
    retry: false,
    staleTime: Infinity,
  });
}
export function useSettlements(batchId: string | undefined) {
  return useQuery({
    queryKey: ['settlements', batchId],
    queryFn: ({ signal }) => api.listSettlements(batchId!, signal),
    enabled: Boolean(batchId),
    retry: false,
    staleTime: Infinity,
  });
}
export function useExceptions(batchId: string | undefined) {
  return useQuery({
    queryKey: ['exceptions', batchId],
    queryFn: ({ signal }) => api.listExceptions(batchId!, signal),
    enabled: Boolean(batchId),
    retry: false,
    staleTime: Infinity,
  });
}
export function useSettlement(
  batchId: string | undefined,
  settlementId: string | undefined,
) {
  return useQuery({
    queryKey: ['settlement', batchId, settlementId],
    queryFn: ({ signal }) => api.getSettlement(batchId!, settlementId!, signal),
    enabled: Boolean(batchId && settlementId),
    retry: false,
    staleTime: Infinity,
  });
}

export function useInvestigations(
  batchId: string | undefined,
  settlementId: string | undefined,
) {
  return useQuery({
    queryKey: ['investigations', batchId, settlementId],
    queryFn: ({ signal }) => api.listInvestigations(batchId!, settlementId!, signal),
    enabled: Boolean(batchId && settlementId),
    retry: false,
    staleTime: 0,
  });
}

export function useInvestigationEligibility(
  batchId: string | undefined,
  settlementId: string | undefined,
) {
  return useQuery({
    queryKey: ['investigation-eligibility', batchId, settlementId],
    queryFn: ({ signal }) =>
      api.getInvestigationEligibility(batchId!, settlementId!, signal),
    enabled: Boolean(batchId && settlementId),
    retry: false,
    staleTime: 0,
  });
}

export function useEffectiveReview(
  batchId: string | undefined,
  settlementId: string | undefined,
) {
  return useQuery({
    queryKey: ['effective-review', batchId, settlementId],
    queryFn: ({ signal }) => api.getEffectiveReview(batchId!, settlementId!, signal),
    enabled: Boolean(batchId && settlementId),
    retry: false,
    staleTime: 0,
  });
}

export function useRunInvestigation(batchId: string, settlementId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.runInvestigation(batchId, settlementId),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({
          queryKey: ['investigations', batchId, settlementId],
          refetchType: 'active',
        }),
        client.invalidateQueries({
          queryKey: ['effective-review', batchId, settlementId],
          refetchType: 'active',
        }),
        client.invalidateQueries({
          queryKey: ['investigation-eligibility', batchId, settlementId],
          refetchType: 'active',
        }),
      ]);
    },
  });
}

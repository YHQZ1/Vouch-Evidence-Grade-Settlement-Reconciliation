import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export function useBatch(batchId: string | undefined) {
  return useQuery({
    queryKey: ["batch", batchId],
    queryFn: ({ signal }) => api.getBatch(batchId!, signal),
    enabled: Boolean(batchId),
    retry: false,
    staleTime: 2_000,
  });
}
export function useResult(batchId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["result", batchId],
    queryFn: ({ signal }) => api.getResult(batchId!, signal),
    enabled: Boolean(batchId) && enabled,
    retry: false,
    staleTime: Infinity,
  });
}
export function useSettlements(batchId: string | undefined) {
  return useQuery({
    queryKey: ["settlements", batchId],
    queryFn: ({ signal }) => api.listSettlements(batchId!, signal),
    enabled: Boolean(batchId),
    retry: false,
    staleTime: Infinity,
  });
}
export function useExceptions(batchId: string | undefined) {
  return useQuery({
    queryKey: ["exceptions", batchId],
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
    queryKey: ["settlement", batchId, settlementId],
    queryFn: ({ signal }) => api.getSettlement(batchId!, settlementId!, signal),
    enabled: Boolean(batchId && settlementId),
    retry: false,
    staleTime: Infinity,
  });
}

import type { components, operations } from './generated';

export type SourceKind = components['schemas']['SourceKind'];
export type BatchStatus = components['schemas']['BatchResponse']['status'];
export type Readiness = components['schemas']['CloseAssessment']['readiness'];
export type ResolutionState = components['schemas']['ResolutionState'];
export type EvidenceStatus = components['schemas']['EvidenceLinkStatus'];

export type ApiError = components['schemas']['ApiError'];
export type ErrorEnvelope = components['schemas']['ErrorEnvelope'];
export type SourceResponse = components['schemas']['SourceResponse'];
export type FailureResponse = components['schemas']['FailureResponse'];
export type BatchLinks = components['schemas']['BatchLinks'];
export type BatchResponse = components['schemas']['BatchResponse'];
export type SourceUploadResponse = components['schemas']['SourceUploadResponse'];
export type ReconciliationRunResponse =
  components['schemas']['ReconciliationRunResponse'];
export type Money = components['schemas']['Money'];
export type CalculatedValue = components['schemas']['CalculatedValue'];
export type CandidateSignal = components['schemas']['CandidateSignal'];
export type SettlementAggregate = components['schemas']['SettlementAggregate'];
export type CandidateBankLink = components['schemas']['CandidateBankLink'];
export type EvidenceLink = components['schemas']['EvidenceLink'];
export type LedgerEvidenceAssignment =
  components['schemas']['LedgerEvidenceAssignment'];
export type AccountingControlResult = components['schemas']['AccountingControlResult'];
export type ExceptionRecord = components['schemas']['ExceptionRecord'];
export type SettlementDecision = components['schemas']['SettlementDecision'];
export type AuditEvent = components['schemas']['AuditEvent'];
export type SettlementResult = components['schemas']['SettlementResult'];
export type SourceFingerprint = components['schemas']['SourceFingerprint'];
export type IngestionSummary = components['schemas']['IngestionSummary'];
export type CloseAssessment = components['schemas']['CloseAssessment'];
export type BatchResult = components['schemas']['BatchResult'];
export type CloseReadinessResponse = components['schemas']['CloseReadinessResponse'];
export type InvestigationEligibility =
  components['schemas']['InvestigationEligibility'];
export type AgentRun = components['schemas']['AgentRun'];
export type InvestigationResponse = JsonSuccess<'runInvestigation'>;
export type InvestigationPage = JsonSuccess<'listSettlementInvestigations'>;
export type BatchInvestigationPage = JsonSuccess<'listBatchInvestigations'>;
export type EffectiveReview = components['schemas']['EffectiveReview'];
export type EffectiveReviewResponse = JsonSuccess<'getEffectiveReview'>;

export type Page<T> = {
  batch_id: string;
  items: T[];
  total: number;
  offset: number;
  limit: number;
  next_offset?: number | null;
};

export type CompleteCollection<T> = {
  batch_id: string;
  items: T[];
  total: number;
};

export type JsonSuccess<Operation extends keyof operations> =
  operations[Operation] extends {
    responses: { 200: { content: { 'application/json': infer Body } } };
  }
    ? Body
    : operations[Operation] extends {
          responses: { 201: { content: { 'application/json': infer Body } } };
        }
      ? Body
      : never;

export type CreateBatchRequest =
  operations['createBatch']['requestBody']['content']['application/json'];
export type SettlementPage = JsonSuccess<'listSettlements'>;
export type ExceptionPage = JsonSuccess<'listExceptions'>;
export type AuditPage = JsonSuccess<'listAuditEvents'>;
export type InvestigationEligibilityResponse =
  JsonSuccess<'getInvestigationEligibility'>;

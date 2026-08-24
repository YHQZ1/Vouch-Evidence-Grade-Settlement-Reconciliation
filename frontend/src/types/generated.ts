/** Generated from src/types/openapi.json. Do not edit manually. */
export type paths = {
  '/api/v1/batches': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /**
     * Create an empty reconciliation batch
     * @description Creates a process-local batch with an explicit evaluation clock.
     */
    post: operations['createBatch'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get batch lifecycle and source readiness */
    get: operations['getBatch'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/audit-events': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List append-only audit events in sequence order */
    get: operations['listAuditEvents'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/close-readiness': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get the policy-derived close-readiness assessment */
    get: operations['getCloseReadiness'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/effective-review': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get effective review projections for a batch */
    get: operations['listEffectiveReviews'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/exceptions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List deterministic exceptions with optional filters */
    get: operations['listExceptions'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/exports/audit-events': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Download append-only audit events as canonical JSON */
    get: operations['exportAuditEvents'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/exports/exceptions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Download deterministic exceptions as canonical JSON */
    get: operations['exportExceptions'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/exports/investigations': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Download bounded investigation history and audit events */
    get: operations['exportInvestigations'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/exports/reconciliation-result': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Download the complete canonical reconciliation result */
    get: operations['exportReconciliationResult'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/investigations': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List append-only investigations for a batch */
    get: operations['listBatchInvestigations'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/reconciliation-runs': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Run deterministic reconciliation synchronously */
    post: operations['runReconciliation'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/result': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get the immutable complete reconciliation result */
    get: operations['getReconciliationResult'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/settlements': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List settlements in deterministic order */
    get: operations['listSettlements'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/settlements/{settlement_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get one settlement by its source identifier */
    get: operations['getSettlement'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/settlements/{settlement_id}/effective-review': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get base and verifier-owned effective review state */
    get: operations['getEffectiveReview'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List append-only investigations for one settlement */
    get: operations['listSettlementInvestigations'];
    put?: never;
    /**
     * Run one bounded investigation for an eligible settlement
     * @description Invokes the configured local provider only for a deterministic needs_review settlement. The provider can propose or abstain; only the verifier can create an effective decision.
     */
    post: operations['runInvestigation'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations/eligibility': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get server-owned investigation eligibility */
    get: operations['getInvestigationEligibility'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/batches/{batch_id}/sources/{source_kind}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    /**
     * Upload or retry one immutable batch source
     * @description Send the bounded raw file as the request body. Set X-Source-Filename to preserve the source filename as metadata.
     */
    put: operations['putBatchSource'];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/healthz': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Check service health */
    get: operations['healthz'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
};

export type webhooks = Record<string, never>;

export type components = {
  schemas: {
    /** Abstention */
    Abstention: {
      /** Explanation */
      explanation: string;
      /** Reason Code */
      reason_code: string;
    };
    /** AccountingControlResult */
    AccountingControlResult: {
      /**
       * Candidate Ledger Source Record Ids
       * @default []
       */
      candidate_ledger_source_record_ids: string[];
      clearing_residual: components['schemas']['Money'];
      /**
       * Complete Evidence
       * @default false
       */
      complete_evidence: boolean;
      /**
       * Duplicate Line Ids
       * @default []
       */
      duplicate_line_ids: string[];
      /**
       * Fee Booking Mismatch
       * @default false
       */
      fee_booking_mismatch: boolean;
      /**
       * Fee Tax Mismatch
       * @default false
       */
      fee_tax_mismatch: boolean;
      /**
       * Journal Ids
       * @default []
       */
      journal_ids: string[];
      /**
       * Journal Unbalanced Ids
       * @default []
       */
      journal_unbalanced_ids: string[];
      /**
       * Linked Ledger Source Record Ids
       * @default []
       */
      linked_ledger_source_record_ids: string[];
      /**
       * Missing Gateway Entity Ids
       * @default []
       */
      missing_gateway_entity_ids: string[];
      /**
       * Missing Settlement Posting
       * @default false
       */
      missing_settlement_posting: boolean;
      /**
       * Movement Evidence
       * @default []
       */
      movement_evidence: components['schemas']['LedgerEvidenceAssignment'][];
      /**
       * Reasons
       * @default []
       */
      reasons: components['schemas']['ReasonCode'][];
      /** Settlement Id */
      settlement_id: string;
      /** Settlement Posting Journal Id */
      settlement_posting_journal_id?: string | null;
      /**
       * Settlement Posting Source Record Ids
       * @default []
       */
      settlement_posting_source_record_ids: string[];
      /**
       * Tax Booking Mismatch
       * @default false
       */
      tax_booking_mismatch: boolean;
      /**
       * Unknown Account Codes
       * @default []
       */
      unknown_account_codes: string[];
    };
    /** AgentAuditEvent */
    AgentAuditEvent: {
      /** Audit Id */
      audit_id: string;
      /** Batch Id */
      batch_id: string;
      /** Cited Source Record Ids */
      cited_source_record_ids: string[];
      effective_state: components['schemas']['ResolutionState'];
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
      /** Event Type */
      event_type: string;
      prior_state: components['schemas']['ResolutionState'];
      /** Reason Codes */
      reason_codes: components['schemas']['ReasonCode'][];
      /** Run Id */
      run_id: string;
      /** Sequence Number */
      sequence_number: number;
      /** Settlement Id */
      settlement_id: string;
      /** Source Fingerprints */
      source_fingerprints: string[];
    };
    /** AgentRun */
    AgentRun: {
      /** Batch Id */
      batch_id: string;
      /**
       * Completed At
       * Format: date-time
       */
      completed_at: string;
      /** Configured Model Identifier */
      configured_model_identifier?: string | null;
      eligibility: components['schemas']['InvestigationEligibility'];
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
      /** Failure Metadata */
      failure_metadata?: string | null;
      /** Failure Reason Code */
      failure_reason_code?: string | null;
      hypothesis?: components['schemas']['StructuredEvidenceHypothesis'] | null;
      /**
       * Model Latency Ms
       * @default 0
       */
      model_latency_ms: number;
      /**
       * Model Mode
       * @enum {string}
       */
      model_mode: 'disabled' | 'local';
      /** Prompt Version */
      prompt_version: string;
      /** @default disabled */
      provider_provenance: components['schemas']['ProviderProvenance'];
      /** Run Id */
      run_id: string;
      /** Schema Version */
      schema_version: string;
      /** Sequence Number */
      sequence_number: number;
      /** Settlement Id */
      settlement_id: string;
      /** Source Fingerprints */
      source_fingerprints: string[];
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      status: components['schemas']['InvestigationStatus'];
      /**
       * Steps
       * @default []
       */
      steps: components['schemas']['AgentStep'][];
      /**
       * Tool Call Count
       * @default 0
       */
      tool_call_count: number;
      /** Tool Version */
      tool_version: string;
      /**
       * Total Duration Ms
       * @default 0
       */
      total_duration_ms: number;
      verification?: components['schemas']['DeterministicVerificationResult'] | null;
      /** Verifier Version */
      verifier_version: string;
    };
    /** AgentStep */
    AgentStep: {
      abstention?: components['schemas']['Abstention'] | null;
      /**
       * Action Type
       * @enum {string}
       */
      action_type: 'tool_call' | 'hypothesis' | 'abstain' | 'invalid';
      /**
       * Duration Ms
       * @default 0
       */
      duration_ms: number;
      /** Failure Reason Code */
      failure_reason_code?: string | null;
      hypothesis?: components['schemas']['StructuredEvidenceHypothesis'] | null;
      request?: components['schemas']['ToolRequest'] | null;
      /** Sequence Number */
      sequence_number: number;
      tool_result?: components['schemas']['ToolResult'] | null;
    };
    /** ApiError */
    ApiError: {
      /** Code */
      code: string;
      /**
       * Details
       * @default []
       */
      details: {
        [key: string]: string;
      }[];
      /** Message */
      message: string;
    };
    /** AuditEvent */
    AuditEvent: {
      /** Audit Id */
      audit_id: string;
      /** Batch Id */
      batch_id: string;
      /** Calculated Values */
      calculated_values: components['schemas']['CalculatedValue'][];
      /** Candidate Accepted */
      candidate_accepted?: boolean | null;
      /** Candidate Score */
      candidate_score?: number | null;
      /**
       * Candidate Signals
       * @default []
       */
      candidate_signals: components['schemas']['CandidateSignal'][];
      /** Cited Source Record Ids */
      cited_source_record_ids: string[];
      /** Decision Type */
      decision_type: string;
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
      /**
       * Input Fingerprints
       * @default []
       */
      input_fingerprints: string[];
      /** Policy Version */
      policy_version: string;
      prior_state: components['schemas']['ResolutionState'] | null;
      /** Reason Codes */
      reason_codes: components['schemas']['ReasonCode'][];
      resulting_state: components['schemas']['ResolutionState'] | null;
      /** Rule Id */
      rule_id: string;
      /** Rule Version */
      rule_version: string;
      /** Schema Version */
      schema_version: string;
      /** Sequence Number */
      sequence_number: number;
      /** Settlement Id */
      settlement_id: string | null;
    };
    /**
     * AuditEventExportResponse
     * @description Canonical JSON shape emitted by the audit-event export endpoint.
     */
    AuditEventExportResponse: {
      /** Audit Events */
      audit_events: components['schemas']['AuditEvent'][];
      /** Batch Id */
      batch_id: string;
    };
    /** AuditEventListResponse */
    AuditEventListResponse: {
      /** Batch Id */
      batch_id: string;
      /** Items */
      items: components['schemas']['AuditEvent'][];
      /** Limit */
      limit: number;
      /** Next Offset */
      next_offset?: number | null;
      /** Offset */
      offset: number;
      /** Total */
      total: number;
    };
    /**
     * BankDirection
     * @enum {string}
     */
    BankDirection: 'credit' | 'debit';
    /** BatchLinks */
    BatchLinks: {
      /** Audit Events */
      audit_events: string;
      /** Audit Events Export */
      audit_events_export: string;
      /** Close Readiness */
      close_readiness: string;
      /** Exceptions */
      exceptions: string;
      /** Exceptions Export */
      exceptions_export: string;
      /** Reconciliation Export */
      reconciliation_export: string;
      /** Result */
      result: string;
      /** Run */
      run: string;
      /** Self */
      self: string;
      /** Settlements */
      settlements: string;
    };
    /** BatchResponse */
    BatchResponse: {
      /** Batch Id */
      batch_id: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
      failure?: components['schemas']['FailureResponse'] | null;
      /** Lifecycle Sequence */
      lifecycle_sequence: number;
      links: components['schemas']['BatchLinks'];
      /** Required Sources */
      required_sources: string[];
      /** Result Available */
      result_available: boolean;
      /** Result Batch Id */
      result_batch_id?: string | null;
      /** Sources */
      sources: components['schemas']['SourceResponse'][];
      /**
       * Status
       * @enum {string}
       */
      status: 'awaiting_sources' | 'ready' | 'running' | 'completed' | 'failed';
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
    };
    /** BatchResult */
    BatchResult: {
      /**
       * Accepted Evidence Links
       * @default []
       */
      accepted_evidence_links: components['schemas']['EvidenceLink'][];
      /**
       * Accounting Controls
       * @default []
       */
      accounting_controls: components['schemas']['AccountingControlResult'][];
      /**
       * Audit Events
       * @default []
       */
      audit_events: components['schemas']['AuditEvent'][];
      /** Batch Id */
      batch_id: string;
      close_readiness: components['schemas']['CloseAssessment'];
      /**
       * Decisions
       * @default []
       */
      decisions: components['schemas']['SettlementDecision'][];
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
      /**
       * Exceptions
       * @default []
       */
      exceptions: components['schemas']['ExceptionRecord'][];
      /**
       * Excluded Records
       * @default []
       */
      excluded_records: components['schemas']['ExcludedRecord'][];
      /**
       * Explained Value Subunits
       * @default 0
       */
      explained_value_subunits: number;
      /** Ingestion */
      ingestion: components['schemas']['IngestionSummary'][];
      /**
       * Pending Value Subunits
       * @default 0
       */
      pending_value_subunits: number;
      /** Policy Version */
      policy_version: string;
      /**
       * Proposed Evidence Links
       * @default []
       */
      proposed_evidence_links: components['schemas']['EvidenceLink'][];
      /**
       * Rejected Candidates
       * @default []
       */
      rejected_candidates: components['schemas']['CandidateBankLink'][];
      /**
       * Rejected Source Rows
       * @default []
       */
      rejected_source_rows: components['schemas']['RejectedSourceRow'][];
      /** Rule Version */
      rule_version: string;
      /** Schema Version */
      schema_version: string;
      /**
       * Settlement Aggregates
       * @default []
       */
      settlement_aggregates: components['schemas']['SettlementAggregate'][];
      /**
       * Settlements
       * @default []
       */
      settlements: components['schemas']['SettlementResult'][];
      /** Source Fingerprints */
      source_fingerprints: components['schemas']['SourceFingerprint'][];
      /**
       * Unresolved Value Subunits
       * @default 0
       */
      unresolved_value_subunits: number;
      /**
       * Verified Value Subunits
       * @default 0
       */
      verified_value_subunits: number;
    };
    /** CalculatedValue */
    CalculatedValue: {
      /** Name */
      name: string;
      /** Value */
      value: string;
    };
    /** CandidateBankLink */
    CandidateBankLink: {
      /** Accepted */
      accepted: boolean;
      /** Bank Row Id */
      bank_row_id: string;
      /** Bank Source Record Id */
      bank_source_record_id: string;
      /**
       * Rejection Reasons
       * @default []
       */
      rejection_reasons: components['schemas']['ReasonCode'][];
      /**
       * Score
       * @default 0
       */
      score: number;
      /** Settlement Aggregate Id */
      settlement_aggregate_id: string;
      /** Settlement Id */
      settlement_id: string;
      /**
       * Signals
       * @default []
       */
      signals: components['schemas']['CandidateSignal'][];
    };
    /** CandidateSignal */
    CandidateSignal: {
      /** Name */
      name: string;
      /** Satisfied */
      satisfied: boolean;
      /** Value */
      value: string;
      /**
       * Weight
       * @default 0
       */
      weight: number;
    };
    /** CloseAssessment */
    CloseAssessment: {
      /**
       * Batch Total Abs Value Subunits
       * @default 0
       */
      batch_total_abs_value_subunits: number;
      /**
       * Blocking Exception Ids
       * @default []
       */
      blocking_exception_ids: string[];
      /**
       * Explained Value Subunits
       * @default 0
       */
      explained_value_subunits: number;
      /**
       * Pending Value Subunits
       * @default 0
       */
      pending_value_subunits: number;
      /**
       * Permitted Exception Ids
       * @default []
       */
      permitted_exception_ids: string[];
      readiness: components['schemas']['CloseReadiness'];
      /**
       * Unresolved Value Subunits
       * @default 0
       */
      unresolved_value_subunits: number;
      /**
       * Verified Value Subunits
       * @default 0
       */
      verified_value_subunits: number;
    };
    /**
     * CloseReadiness
     * @enum {string}
     */
    CloseReadiness: 'READY' | 'READY_WITH_EXCEPTIONS' | 'BLOCKED';
    /** CloseReadinessResponse */
    CloseReadinessResponse: {
      assessment: components['schemas']['CloseAssessment'];
      /** Batch Id */
      batch_id: string;
      /** Result Batch Id */
      result_batch_id: string;
    };
    /** CreateBatchRequest */
    CreateBatchRequest: {
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
    };
    /**
     * Currency
     * @description Valid currency codes usable by the value object.
     * @enum {string}
     */
    Currency: 'INR' | 'USD';
    /** DeterministicVerificationResult */
    DeterministicVerificationResult: {
      /** Accepted */
      accepted: boolean;
      canonical_currency?: components['schemas']['Currency'] | null;
      canonical_direction?: components['schemas']['BankDirection'] | null;
      /** Canonical Signed Amount Subunits */
      canonical_signed_amount_subunits?: number | null;
      /**
       * Cited Source Record Ids
       * @default []
       */
      cited_source_record_ids: string[];
      /** Explanation */
      explanation: string;
      /** Proposed Bank Source Record Id */
      proposed_bank_source_record_id?: string | null;
      /**
       * Reason Codes
       * @default []
       */
      reason_codes: components['schemas']['ReasonCode'][];
      /** Settlement Id */
      settlement_id: string;
    };
    /** EffectiveAgentVerifiedDecision */
    EffectiveAgentVerifiedDecision: {
      /** Batch Id */
      batch_id: string;
      /** Cited Source Record Ids */
      cited_source_record_ids: string[];
      /** Decision Id */
      decision_id: string;
      /**
       * Effective State
       * @constant
       */
      effective_state: 'cleared_with_explanation';
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
      prior_deterministic_state: components['schemas']['ResolutionState'];
      /** Prompt Version */
      prompt_version: string;
      /** Reason Codes */
      reason_codes: components['schemas']['ReasonCode'][];
      /** Run Id */
      run_id: string;
      /** Sequence Number */
      sequence_number: number;
      /** Settlement Id */
      settlement_id: string;
      /** Source Fingerprints */
      source_fingerprints: string[];
      /** Tool Version */
      tool_version: string;
      /** Verifier Version */
      verifier_version: string;
    };
    /** EffectiveReview */
    EffectiveReview: {
      accepted_decision?:
        components['schemas']['EffectiveAgentVerifiedDecision'] | null;
      base_close_assessment: components['schemas']['CloseAssessment'];
      base_settlement: components['schemas']['SettlementResult'];
      base_state: components['schemas']['ResolutionState'];
      /** Batch Id */
      batch_id: string;
      effective_close_assessment: components['schemas']['CloseAssessment'];
      effective_settlement: components['schemas']['SettlementResult'];
      effective_state: components['schemas']['ResolutionState'];
      /** Settlement Id */
      settlement_id: string;
    };
    /** EffectiveReviewListResponse */
    EffectiveReviewListResponse: {
      /** Batch Id */
      batch_id: string;
      /** Items */
      items: components['schemas']['EffectiveReview'][];
      /** Limit */
      limit: number;
      /** Next Offset */
      next_offset?: number | null;
      /** Offset */
      offset: number;
      /** Total */
      total: number;
    };
    /** EffectiveReviewResponse */
    EffectiveReviewResponse: {
      review: components['schemas']['EffectiveReview'];
    };
    /** ErrorEnvelope */
    ErrorEnvelope: {
      error: components['schemas']['ApiError'];
    };
    /** EvidenceLink */
    EvidenceLink: {
      /**
       * Calculated Values
       * @default []
       */
      calculated_values: components['schemas']['CalculatedValue'][];
      /** Candidate Score */
      candidate_score?: number | null;
      /**
       * Candidate Signals
       * @default []
       */
      candidate_signals: components['schemas']['CandidateSignal'][];
      /** Gateway Source Record Id */
      gateway_source_record_id?: string | null;
      /** Journal Id */
      journal_id?: string | null;
      /** Link Id */
      link_id: string;
      /**
       * Reason Codes
       * @default []
       */
      reason_codes: components['schemas']['ReasonCode'][];
      /** Relationship Type */
      relationship_type: string;
      /** Source Record Ids */
      source_record_ids: string[];
      status: components['schemas']['EvidenceLinkStatus'];
    };
    /**
     * EvidenceLinkStatus
     * @enum {string}
     */
    EvidenceLinkStatus: 'verified' | 'proposed' | 'rejected';
    /**
     * ExceptionExportResponse
     * @description Canonical JSON shape emitted by the exception export endpoint.
     */
    ExceptionExportResponse: {
      /** Batch Id */
      batch_id: string;
      /** Exceptions */
      exceptions: components['schemas']['ExceptionRecord'][];
    };
    /** ExceptionListResponse */
    ExceptionListResponse: {
      /** Batch Id */
      batch_id: string;
      /** Items */
      items: components['schemas']['ExceptionRecord'][];
      /** Limit */
      limit: number;
      /** Next Offset */
      next_offset?: number | null;
      /** Offset */
      offset: number;
      /** Total */
      total: number;
    };
    /** ExceptionRecord */
    ExceptionRecord: {
      /** Blocking */
      blocking: boolean;
      /** Exception Id */
      exception_id: string;
      /** Explanation */
      explanation: string;
      /** Material */
      material: boolean;
      reason_code: components['schemas']['ReasonCode'];
      /** Settlement Id */
      settlement_id: string | null;
      /**
       * Source Record Ids
       * @default []
       */
      source_record_ids: string[];
      /**
       * Value Subunits
       * @default 0
       */
      value_subunits: number;
    };
    /** ExcludedRecord */
    ExcludedRecord: {
      /** Explanation */
      explanation: string;
      reason_code: components['schemas']['ReasonCode'];
      source_kind: components['schemas']['SourceKind'];
      /** Source Record Id */
      source_record_id: string;
    };
    /** FailureResponse */
    FailureResponse: {
      /** Code */
      code: string;
      /** Message */
      message: string;
      /** Sequence */
      sequence: number;
    };
    /**
     * HealthResponse
     * @description Stable response contract for service health checks.
     */
    HealthResponse: {
      /** Api Version */
      api_version: string;
      /** Service */
      service: string;
      /**
       * Status
       * @constant
       */
      status: 'ok';
    };
    /** IngestionSummary */
    IngestionSummary: {
      /** Accepted Row Count */
      accepted_row_count: number;
      /**
       * Duplicate Identifier Count
       * @default 0
       */
      duplicate_identifier_count: number;
      /** Fatal Error */
      fatal_error?: string | null;
      /** Rejected Row Count */
      rejected_row_count: number;
      /** Row Count */
      row_count: number;
      source_kind: components['schemas']['SourceKind'];
      /** Source Name */
      source_name: string;
    };
    /**
     * InvestigationEligibility
     * @description Deterministic eligibility decision for one settlement.
     */
    InvestigationEligibility: {
      /** Batch Id */
      batch_id: string;
      current_state: components['schemas']['ResolutionState'];
      /** Eligible */
      eligible: boolean;
      /** Explanation */
      explanation: string;
      /**
       * Provider Available
       * @default true
       */
      provider_available: boolean;
      /**
       * Reason Codes
       * @default []
       */
      reason_codes: components['schemas']['ReasonCode'][];
      /** Settlement Id */
      settlement_id: string;
    };
    /** InvestigationExportResponse */
    InvestigationExportResponse: {
      /** Audit Events */
      audit_events: components['schemas']['AgentAuditEvent'][];
      /** Batch Id */
      batch_id: string;
      /** Investigations */
      investigations: components['schemas']['AgentRun'][];
      operational: components['schemas']['OperationalMeasurements'];
      provider_provenance: components['schemas']['ProviderProvenance'];
    };
    /** InvestigationListResponse */
    InvestigationListResponse: {
      /** Batch Id */
      batch_id: string;
      /** Items */
      items: components['schemas']['AgentRun'][];
      /** Limit */
      limit: number;
      /** Next Offset */
      next_offset?: number | null;
      /** Offset */
      offset: number;
      /** Total */
      total: number;
    };
    /** InvestigationResponse */
    InvestigationResponse: {
      eligibility: components['schemas']['InvestigationEligibility'];
      run?: components['schemas']['AgentRun'] | null;
    };
    /**
     * InvestigationStatus
     * @description String values used by the append-only run repository.
     * @enum {string}
     */
    InvestigationStatus:
      | 'created'
      | 'running'
      | 'completed'
      | 'abstained'
      | 'rejected'
      | 'failed'
      | 'cancelled';
    /** LedgerEvidenceAssignment */
    LedgerEvidenceAssignment: {
      /** Gateway Entity Id */
      gateway_entity_id: string;
      /** Gateway Source Record Id */
      gateway_source_record_id: string;
      /** Journal Id */
      journal_id?: string | null;
      /**
       * Ledger Line Ids
       * @default []
       */
      ledger_line_ids: string[];
      /**
       * Ledger Source Record Ids
       * @default []
       */
      ledger_source_record_ids: string[];
      /**
       * Reason Codes
       * @default []
       */
      reason_codes: components['schemas']['ReasonCode'][];
      status: components['schemas']['EvidenceLinkStatus'];
    };
    /**
     * Money
     * @description An integer amount in one currency's smallest unit.
     *
     *     Signed values are allowed because financial movements need both directions.
     *     Individual source debit/credit fields use
     *     non-negative integers and expose this value object through derived
     *     properties on their records.
     */
    Money: {
      currency: components['schemas']['Currency'];
      /** Subunits */
      subunits: number;
    };
    /** OperationalMeasurements */
    OperationalMeasurements: {
      /**
       * Accepted Verification Count
       * @default 0
       */
      accepted_verification_count: number;
      /** Ai False Clear Count */
      ai_false_clear_count?: number | null;
      /** Ai False Clear Value Subunits */
      ai_false_clear_value_subunits?: number | null;
      /**
       * Cancellation Count
       * @default 0
       */
      cancellation_count: number;
      /**
       * Eligible Case Count
       * @default 0
       */
      eligible_case_count: number;
      /**
       * Invoked Case Count
       * @default 0
       */
      invoked_case_count: number;
      /**
       * Model Abstention Count
       * @default 0
       */
      model_abstention_count: number;
      /**
       * Model Latency Ms
       * @default 0
       */
      model_latency_ms: number;
      /**
       * Provider Unavailable Count
       * @default 0
       */
      provider_unavailable_count: number;
      /**
       * Run Count
       * @default 0
       */
      run_count: number;
      /**
       * Schema Failure Count
       * @default 0
       */
      schema_failure_count: number;
      /**
       * Timeout Or Budget Exhaustion Count
       * @default 0
       */
      timeout_or_budget_exhaustion_count: number;
      /**
       * Tool Call Count
       * @default 0
       */
      tool_call_count: number;
      /**
       * Total Latency Ms
       * @default 0
       */
      total_latency_ms: number;
      /**
       * Verifier Rejection Count
       * @default 0
       */
      verifier_rejection_count: number;
    };
    /**
     * ProviderProvenance
     * @description Server-owned origin of an investigation model invocation.
     * @enum {string}
     */
    ProviderProvenance: 'disabled' | 'ollama' | 'scripted_test';
    /**
     * ReasonCode
     * @description Stable machine-readable explanations for future runtime decisions.
     * @enum {string}
     */
    ReasonCode:
      | 'exact_evidence_verified'
      | 'fee_tax_netted'
      | 'refund_netted'
      | 'utr_missing'
      | 'utr_conflicting_or_malformed'
      | 'pending_within_sla'
      | 'overdue_bank_credit_missing'
      | 'bank_candidate_ambiguity'
      | 'ledger_line_missing'
      | 'ledger_line_duplicated'
      | 'journal_unbalanced'
      | 'fee_booking_mismatch'
      | 'tax_booking_mismatch'
      | 'ledger_account_role_mismatch'
      | 'ledger_direction_mismatch'
      | 'balance_account_conflict'
      | 'malformed_source_record'
      | 'duplicate_business_identifier'
      | 'unknown_account_role'
      | 'wrong_direction'
      | 'currency_mismatch'
      | 'amount_mismatch'
      | 'outside_timing_window'
      | 'conflicting_reference'
      | 'insufficient_uniqueness'
      | 'record_already_consumed'
      | 'missing_bank_credit'
      | 'clearing_residual'
      | 'required_ledger_evidence_missing'
      | 'out_of_scope'
      | 'unrelated_bank_record'
      | 'ledger_evidence_reused'
      | 'ledger_evidence_ambiguous'
      | 'stronger_candidate_selected'
      | 'agent_verified'
      | 'agent_verification_rejected';
    /** ReconciliationRunResponse */
    ReconciliationRunResponse: {
      /** Batch Id */
      batch_id: string;
      failure?: components['schemas']['FailureResponse'] | null;
      links: components['schemas']['BatchLinks'];
      /** Result Available */
      result_available: boolean;
      /** Result Batch Id */
      result_batch_id?: string | null;
      /**
       * Status
       * @enum {string}
       */
      status: 'awaiting_sources' | 'ready' | 'running' | 'completed' | 'failed';
    };
    /** RejectedSourceRow */
    RejectedSourceRow: {
      lineage: components['schemas']['SourceLineage'];
      /** Raw Values */
      raw_values: {
        [key: string]: string | null;
      };
      reason_code: components['schemas']['ReasonCode'];
      source_kind: components['schemas']['SourceKind'];
      /** Validation Reason */
      validation_reason: string;
    };
    /**
     * ResolutionState
     * @enum {string}
     */
    ResolutionState:
      | 'auto_cleared'
      | 'cleared_with_explanation'
      | 'pending_within_sla'
      | 'needs_review'
      | 'critical_exception'
      | 'excluded';
    /** SettlementAggregate */
    SettlementAggregate: {
      /** Aggregate Id */
      aggregate_id: string;
      /** Balance Account Id */
      balance_account_id: string | null;
      currency: components['schemas']['Currency'];
      /** Gross Activity Subunits */
      gross_activity_subunits: number;
      /**
       * Latest Settled At
       * Format: date-time
       */
      latest_settled_at: string;
      /** Member Entity Ids */
      member_entity_ids: string[];
      /** Member Source Record Ids */
      member_source_record_ids: string[];
      /**
       * Normalized Utrs
       * @default []
       */
      normalized_utrs: string[];
      /** Settlement Id */
      settlement_id: string;
      signed_net: components['schemas']['Money'];
      /** Total Credit Subunits */
      total_credit_subunits: number;
      /** Total Debit Subunits */
      total_debit_subunits: number;
      /** Total Fee Subunits */
      total_fee_subunits: number;
      /** Total Tax Subunits */
      total_tax_subunits: number;
      /**
       * Utr Conflict
       * @default false
       */
      utr_conflict: boolean;
    };
    /** SettlementDecision */
    SettlementDecision: {
      /** Aggregate Id */
      aggregate_id: string;
      /** Batch Id */
      batch_id: string;
      /** Calculated Values */
      calculated_values: components['schemas']['CalculatedValue'][];
      /** Cited Source Record Ids */
      cited_source_record_ids: string[];
      /** Decision Id */
      decision_id: string;
      /**
       * Evaluation Clock
       * Format: date-time
       */
      evaluation_clock: string;
      /**
       * Input Fingerprints
       * @default []
       */
      input_fingerprints: string[];
      /** Policy Version */
      policy_version: string;
      /** Reason Codes */
      reason_codes: components['schemas']['ReasonCode'][];
      /** Rule Id */
      rule_id: string;
      /** Rule Version */
      rule_version: string;
      /** Schema Version */
      schema_version: string;
      /** Sequence Number */
      sequence_number: number;
      /** Settlement Id */
      settlement_id: string;
      state: components['schemas']['ResolutionState'];
    };
    /** SettlementListResponse */
    SettlementListResponse: {
      /** Batch Id */
      batch_id: string;
      /** Items */
      items: components['schemas']['SettlementResult'][];
      /** Limit */
      limit: number;
      /** Next Offset */
      next_offset?: number | null;
      /** Offset */
      offset: number;
      /** Total */
      total: number;
    };
    /** SettlementResult */
    SettlementResult: {
      /**
       * Accepted Evidence Links
       * @default []
       */
      accepted_evidence_links: components['schemas']['EvidenceLink'][];
      accounting_control?: components['schemas']['AccountingControlResult'] | null;
      aggregate: components['schemas']['SettlementAggregate'];
      decision: components['schemas']['SettlementDecision'];
      /**
       * Exceptions
       * @default []
       */
      exceptions: components['schemas']['ExceptionRecord'][];
      /**
       * Proposed Evidence Links
       * @default []
       */
      proposed_evidence_links: components['schemas']['EvidenceLink'][];
      /** Reason Codes */
      reason_codes: components['schemas']['ReasonCode'][];
      /**
       * Rejected Candidates
       * @default []
       */
      rejected_candidates: components['schemas']['CandidateBankLink'][];
      state: components['schemas']['ResolutionState'];
      /**
       * Unresolved Value Subunits
       * @default 0
       */
      unresolved_value_subunits: number;
    };
    /** SourceFingerprint */
    SourceFingerprint: {
      /** Byte Count */
      byte_count: number;
      /** Sha256 */
      sha256: string;
      source_kind: components['schemas']['SourceKind'];
      /** Source Name */
      source_name: string;
    };
    /**
     * SourceKind
     * @description Supported source systems.
     * @enum {string}
     */
    SourceKind: 'gateway' | 'bank' | 'ledger' | 'policy';
    /**
     * SourceLineage
     * @description Stable identity and schema metadata for one source row.
     */
    SourceLineage: {
      /**
       * Schema Version
       * @default v1
       * @constant
       */
      schema_version: 'v1';
      /** Source Fingerprint */
      source_fingerprint: string;
      source_kind: components['schemas']['SourceKind'];
      /** Source Name */
      source_name: string;
      /** Source Record Id */
      source_record_id?: string | null;
      /** Source Row Number */
      source_row_number: number;
    };
    /** SourceResponse */
    SourceResponse: {
      /** Byte Count */
      byte_count: number;
      /** Content Type */
      content_type: string;
      /** Filename */
      filename: string;
      /** Sequence */
      sequence: number;
      /** Sha256 */
      sha256: string;
      /** Source Kind */
      source_kind: string;
    };
    /** SourceUploadResponse */
    SourceUploadResponse: {
      /** Batch Id */
      batch_id: string;
      /** Idempotent */
      idempotent: boolean;
      links: components['schemas']['BatchLinks'];
      source: components['schemas']['SourceResponse'];
      /**
       * Status
       * @enum {string}
       */
      status: 'awaiting_sources' | 'ready' | 'running' | 'completed' | 'failed';
    };
    /**
     * StructuredEvidenceHypothesis
     * @description Narrow settlement-to-bank proposal returned by an untrusted model.
     */
    StructuredEvidenceHypothesis: {
      /** Abstention Alternative */
      abstention_alternative: string;
      /** Cited Source Record Ids */
      cited_source_record_ids: string[];
      /** Evidence Claim */
      evidence_claim: string;
      /** Expected Balance Account Id */
      expected_balance_account_id?: string | null;
      expected_currency: components['schemas']['Currency'];
      expected_direction: components['schemas']['BankDirection'];
      /** Expected Signed Amount Subunits */
      expected_signed_amount_subunits: number;
      /**
       * Hypothesis Kind
       * @constant
       */
      hypothesis_kind: 'settlement_to_bank';
      /** Proposed Bank Source Record Id */
      proposed_bank_source_record_id: string;
      /** Settlement Id */
      settlement_id: string;
      timing_claim: components['schemas']['TimingClaim'];
    };
    /** TimingClaim */
    TimingClaim: {
      /**
       * End
       * Format: date-time
       */
      end: string;
      /** Explanation */
      explanation: string;
      /**
       * Start
       * Format: date-time
       */
      start: string;
    };
    /** ToolRequest */
    ToolRequest: {
      /** Arguments */
      arguments?: {
        [key: string]: unknown;
      };
      /** Tool Name */
      tool_name: string;
    };
    /** ToolResult */
    ToolResult: {
      /** Payload */
      payload?: {
        [key: string]: unknown;
      };
      /** Reason Code */
      reason_code?: string | null;
      /**
       * Source Record Ids
       * @default []
       */
      source_record_ids: string[];
      /** Success */
      success: boolean;
      /** Tool Name */
      tool_name: string;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
};

export type $defs = Record<string, never>;

export interface operations {
  createBatch: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateBatchRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['BatchResponse'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  getBatch: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['BatchResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  listAuditEvents: {
    parameters: {
      query?: {
        limit?: number;
        offset?: number;
      };
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['AuditEventListResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  getCloseReadiness: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CloseReadinessResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  listEffectiveReviews: {
    parameters: {
      query?: {
        limit?: number;
        offset?: number;
      };
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['EffectiveReviewListResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  listExceptions: {
    parameters: {
      query?: {
        blocking?: boolean | null;
        limit?: number;
        material?: boolean | null;
        offset?: number;
        reason_code?: string | null;
        settlement_id?: string | null;
      };
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExceptionListResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  exportAuditEvents: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['AuditEventExportResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  exportExceptions: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExceptionExportResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  exportInvestigations: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InvestigationExportResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  exportReconciliationResult: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['BatchResult'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  listBatchInvestigations: {
    parameters: {
      query?: {
        limit?: number;
        offset?: number;
      };
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InvestigationListResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  runReconciliation: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ReconciliationRunResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  getReconciliationResult: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['BatchResult'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  listSettlements: {
    parameters: {
      query?: {
        limit?: number;
        offset?: number;
      };
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['SettlementListResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  getSettlement: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
        settlement_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['SettlementResult'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  getEffectiveReview: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
        settlement_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['EffectiveReviewResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  listSettlementInvestigations: {
    parameters: {
      query?: {
        limit?: number;
        offset?: number;
      };
      header?: never;
      path: {
        batch_id: string;
        settlement_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InvestigationListResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  runInvestigation: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
        settlement_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InvestigationResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  getInvestigationEligibility: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
        settlement_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InvestigationEligibility'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  putBatchSource: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
        source_kind: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': string;
        'text/csv': string;
      };
    };
    responses: {
      /** @description Identical upload retry; no replacement occurred. */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['SourceUploadResponse'];
        };
      };
      /** @description New source stored. */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['SourceUploadResponse'];
        };
      };
      /** @description The requested batch or settlement was not found. */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The requested lifecycle transition or source replacement is not valid. */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The source payload exceeds the configured limit. */
      413: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The source content type is not supported. */
      415: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description The request or source failed explicit validation. */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  healthz: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HealthResponse'];
        };
      };
    };
  };
}

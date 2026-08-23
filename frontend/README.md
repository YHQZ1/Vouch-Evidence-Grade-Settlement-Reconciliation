# Frontend boundary

This directory will contain the Vouch review interface. No frontend implementation
exists yet.

## Initial experience

The MVP interface will support:

1. batch creation and three-source upload;
2. schema and rejected-row feedback;
3. close-readiness and money-at-risk summary;
4. settlement-level Razorpay → Bank → Ledger evidence review;
5. a materiality-ranked exception queue;
6. bounded agent-investigation status and verifier outcome; and
7. report and audit export.

## Planned boundaries

```text
frontend/
├── src/
│   ├── app/              # Routing and application composition
│   ├── features/         # Batch, settlement, exception, and export flows
│   ├── components/       # Shared accessible UI components
│   ├── lib/              # API client and formatting utilities
│   └── types/            # Generated or shared API contracts
└── tests/
```

The interface must communicate status with text and structure rather than color
alone. It must display evidence and reason codes before decorative analytics.

See the [product specification](../docs/product-spec.md) for the complete workflow.

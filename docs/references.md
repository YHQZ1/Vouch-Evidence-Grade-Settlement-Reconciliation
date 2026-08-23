# References and verified assumptions

**Last reviewed:** 2026-08-23

This document separates primary-source facts from Vouch's design assumptions.
Links should be rechecked before the final submission because product behavior and
documentation can change.

## Buildathon brief

- [Razorpay AI Buildathon](https://razorpay.com/buildathon/)

Verified from the official page:

- Track 04 is AI Finance Controller.
- The requested output is an agent that closes one finance-operations loop over a
  batch of at least 50 synthetic records.
- The submission should report throughput, measured accuracy, and unresolved
  exceptions.
- A public repository, architecture, and five-minute pitch are part of showing the
  work.

The application deadline is not stated on the public page at the time of this
review. It should not be repeated in project documentation until manually verified
from the current application form.

## Razorpay settlement model

- [Fetch Settlement Recon Details](https://razorpay.com/docs/api/settlements/fetch-recon/?preferred-country=IN)
- [Settlement FAQs](https://razorpay.com/docs/payments/settlements/faqs/?preferred-country=IN)
- [Settlement webhook events](https://razorpay.com/docs/webhooks/settlements/?preferred-country=IN)

Verified assumptions:

- Reconciliation activity can include payments, refunds, transfers, and
  adjustments.
- The recon response exposes debit, credit, amount, fee, tax, settlement ID,
  settlement UTR, order ID, timestamps, and related metadata.
- Settlement ID groups the activity associated with a settlement.
- UTR is the bank-traceable reference Razorpay recommends for reconciling a
  settlement credit against a bank statement.
- A processed settlement may take up to the documented bank-rail window to appear
  in the bank account; processed is not equivalent to observed bank receipt.
- Domestic and international settlement cycles differ and depend on working-day
  calendars.
- Current Razorpay documentation describes balance segregation and channel-
  specific settlement reporting.

## Vouch design assumptions

These are explicit product choices, not claims about universal accounting:

- The MVP uses INR and standard domestic settlements.
- The synthetic ledger uses a configured Razorpay clearing account.
- Ledger journals are expected to be balanced double-entry records.
- UTR is strong but not sufficient evidence without amount, direction, time, and
  uniqueness validation.
- Similarity generates candidates but cannot independently clear a record.
- Close materiality and timing are versioned demonstration policy inputs.
- Runtime has no access to held-out ground truth.
- AI is optional, local by default, and subordinate to deterministic verification.

## Questions to revalidate before submission

- Current application deadline and submission fields.
- Exact expected pitch-video and repository-access requirements.
- Current test-mode availability for settlement-related APIs.
- Current local-model runtime and model identifier used in the demo.
- Whether balance-account fields are present in the exact synthetic report format
  chosen for the submission.

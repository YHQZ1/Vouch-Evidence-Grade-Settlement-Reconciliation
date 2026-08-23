# Security policy

## Current status

Vouch is an early buildathon prototype intended for synthetic data. It is not yet
approved for production financial records or credentials.

## Reporting a vulnerability

Do not disclose a security issue in a public issue. Use GitHub private
vulnerability reporting when it is enabled for the repository, or contact the
repository owner through a private channel.

Include:

- the affected component;
- reproduction steps;
- expected and observed behavior;
- potential impact on evidence, decisions, or data confidentiality; and
- any suggested mitigation.

## High-priority security properties

- Untrusted CSV content must remain data and cannot issue model or system
  instructions.
- Uploaded source records must not be sent to a remote model by default.
- Runtime code must not access held-out ground-truth labels.
- A model response cannot directly clear a financial exception.
- Exported spreadsheet values must be protected against formula injection.
- Secrets and real financial exports must remain outside version control.
- Input files and decisions must be fingerprinted so evidence substitution is
  detectable.

See [Safety and trust](docs/safety-and-trust.md) for the complete threat model and
control boundaries.

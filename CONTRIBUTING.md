# Contributing

Thanks for helping improve FlowMind AI.

## Principles
- Keep the core skill portable and tool-agnostic.
- Prefer evidence, explicit assumptions, and causal reasoning.
- Keep references modular; load only what a task needs.
- Never include confidential company, customer, employee, or production data.
- Do not present simulations as observed plant performance.
- Preserve safety, regulatory, and quality controls.
- Attribute sources and respect their licences.

## Pull requests
Include the problem, expected behavior, example prompt, evidence, tests for
scripts/calculations, and documentation/changelog updates.

## Tests
```bash
python -m unittest discover -s tests -v
```

FlowMind is decision support. It does not certify engineering calculations,
guarantee business outcomes, or replace qualified review.

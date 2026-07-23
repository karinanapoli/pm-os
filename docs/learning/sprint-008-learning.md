# Sprint 008 Learning — Context is not a prompt

## What changed

PM Studio now treats each document as a source with identity, origin, size, and a
confidentiality level. The model receives those sources inside explicit boundaries
and is instructed to cite factual claims.

## Why this matters to Product Managers

A prompt tells the model what task to perform. Context supplies the evidence it may
use. Mixing the two makes unsupported answers harder to spot.

Before generating:

1. Check which documents are included.
2. Review the confidentiality classifications.
3. Confirm whether the provider is local or external.
4. Compare the estimated context size with the information actually needed.

After generating:

1. Look for `[SRC-XXXXXXXX]` citations beside factual claims.
2. Verify important claims against the cited source.
3. Treat uncited ideas as inferences or recommendations, not facts.
4. Turn missing evidence into explicit discovery questions.

## Adding source metadata

Create `context/.sources.yaml` inside an initiative:

```yaml
sources:
  discovery.md:
    author: Product Research
    confidentiality: confidential
```

Supported classifications are `public`, `internal`, `confidential`, and
`restricted`. Missing classifications default to `internal`.

## Practical exercise

Use two documents that disagree about the same customer need. Generate a PRD, inspect
the citations, and decide which additional research would resolve the contradiction.

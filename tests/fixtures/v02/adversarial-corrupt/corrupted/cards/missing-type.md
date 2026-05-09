---
id: missing-type
title: "Card Missing Epistemic Type"
created: 2026-04-10
confidence: 3
source_tier: 3
domains:
  - corrupted
content_categories:
  - testing
lifecycle: growing
sources:
  - type: url
    ref: "https://example.com/test-source-3"
    title: "Test Source Three"
connects_to: []
tags: [test, missing-field]
author: researcher
---

## Summary
This card is missing the epistemic_type field in its frontmatter.

## Evidence
Intentionally malformed for validation testing.

## Significance
Tests graceful handling of missing required fields.

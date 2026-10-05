# 001. Use Architecture Decision Records

Date: 2026-10-05

Status: Active

## Context

Architectural decisions need a durable, repo-local record near the code
they shape. Product behavior is covered by the code and its tests, not by
separate written specs — this project keeps no feature-spec documents.

## Decision

Record architectural decisions as ADRs in `specs/adr/`, kept small enough
that reading all of them stays practical.

Rules:

1. Name files `NNN-short-title.md` (`000-template.md` is reserved for the
   template). Use the next unused number for a new ADR; don't renumber
   existing ones — except during a deliberate, occasional snapshot pass
   (like this one) that squashes a chain of superseded decisions into
   whichever ADR is actually current, since this project has no other
   readers who need the superseded trail preserved.
2. One decision per ADR.
3. Sections, in order: `# NNN. Title`, `Date`, `Status`, `## Context`,
   `## Decision`, `## Alternatives` (when useful), `## Pros`, `## Cons`,
   `## Links to Related ADRs` (when related ADRs exist).
4. Label links with the relationship (`Depends on`, `Used by`,
   `Constrains`/`Constrained by`, `Refines`/`Refined by`,
   `Supersedes`/`Superseded by`) and keep them bidirectional.
5. Link related issues, PRs, and code instead of copying long material.
6. Outside of a snapshot pass, treat ADRs as historical records — write a
   new one for a changed decision rather than editing an old one in place.

## Alternatives

- Keep decisions in issues, PRs, or commit messages only. Lighter, but
  makes old decisions harder to discover from the repo.
- Write a feature spec per behavior change, kept alongside the ADRs.
  Rejected: with one developer and the behavior already covered by code
  and tests, a second written description of the same behavior is pure
  upkeep cost.

## Pros

Decisions are discoverable and reviewable with the code; small ADRs stay
cheap to write and read as a set.

## Cons

A documentation step for architectural work; the occasional snapshot pass
is itself work.

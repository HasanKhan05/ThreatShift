> **Historical evidence — superseded by Phase 8 synthetic-only redesign.** This note records an earlier release state only. It is not an active instruction, input requirement, or claim for the current synthetic-only study.
# Phase 0 — Foundation Risks and Decisions

## Resolved issue

- **Windows drive-relative paths:** a path such as `C:outside` is not safely project-relative. On non-Windows hosts, a platform-native `Path` check alone can fail to classify that spelling as drive-qualified. Project configuration validation now checks both the native path representation and `PureWindowsPath`; it rejects drive-qualified, anchored, absolute, and parent-traversal paths for local data and artifact directories. The regression test covers both configured directory fields.

## Remaining reproducibility caveat

- **Lock-backed environment:** `uv.lock` fixes the resolved Python dependency set for the documented Phase 0 commands. Reproducibility still depends on running the frozen commands with a supported Python version and retaining the repository configuration and lockfile together. The documented commands validate project mechanics only; they do not validate official CIC-IDS2017 data, provenance, schema, or results.

## Review point

The Phase 0 remediation is included in the revised Phase 0–2 cycle review. The cycle commit and remote-push verification remain release-gate actions for the routing lead.

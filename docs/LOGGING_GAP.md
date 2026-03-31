# Logging Gap: No Centralized Log Aggregation

**Issue ID:** I3
**Date:** 2026-03-31

## Current State

The stack has Prometheus and Grafana for **metrics** collection, but there
is no centralized **log** aggregation. Application logs are written to
stdout/stderr inside containers and are only accessible via
`docker logs` or `kubectl logs`. There is no search, retention, or
alerting on log content.

## Recommended Path

Add **Loki + Promtail** to the existing monitoring stack:

- Promtail runs as a sidecar or DaemonSet and ships container logs to Loki.
- Loki stores and indexes logs with minimal resource overhead.
- Grafana (already deployed) can query Loki alongside Prometheus in the
  same dashboards.

This avoids introducing a separate log UI (e.g., Kibana) and keeps the
tooling consistent.

## Decision Required

This is a human decision -- it affects storage costs, retention policy,
and operational complexity. Options:

1. **Loki + Promtail** (lightweight, Grafana-native)
2. **EFK stack** (Elasticsearch + Fluentd + Kibana -- heavier, more powerful)
3. **Cloud-native** (CloudWatch Logs on AWS -- simplest if already on EKS)

Pick one and add the relevant services to `docker-compose.yml` (local) and
Helm/Kustomize (production).

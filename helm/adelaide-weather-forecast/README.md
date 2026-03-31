# Adelaide Weather Forecast Helm Chart

**Status: In Progress -- Not Usable**

This chart currently contains only `Chart.yaml` and `values.yaml`.
There is no `templates/` directory, so `helm install` will deploy nothing.

The values file documents the intended configuration surface (replicas,
resources, ingress, autoscaling, etc.) and is referenced by the
production deployment workflow, but actual Kubernetes manifests have not
been written yet.

## What is needed

A working chart requires at minimum:

- `templates/deployment.yaml` (API + frontend Deployments)
- `templates/service.yaml` (ClusterIP Services)
- `templates/ingress.yaml` (ALB Ingress)
- `templates/hpa.yaml` (HorizontalPodAutoscaler)
- `templates/_helpers.tpl` (naming and label helpers)

Until those are created, Kubernetes deployments should use the raw
manifests in `k8s/` with Kustomize overlays.

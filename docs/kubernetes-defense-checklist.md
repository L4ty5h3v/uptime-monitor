# Kubernetes Defense Checklist

Этот чеклист нужен для защиты лабы по Kubernetes.

## Что открыть заранее

- API `dev`: [http://10.211.55.9:30080/docs](http://10.211.55.9:30080/docs)
- API health: [http://10.211.55.9:30080/health](http://10.211.55.9:30080/health)
- Grafana: [http://10.211.55.3:3000](http://10.211.55.3:3000)
- Prometheus: [http://10.211.55.3:9090](http://10.211.55.3:9090)

Grafana логин:

- `admin`
- `admin`

## Что показать по порядку

### 1. Kubernetes cluster

На `cp1`:

```bash
kubectl --kubeconfig=/home/master1/.kube/config get nodes -o wide
kubectl --kubeconfig=/home/master1/.kube/config get ns
kubectl --kubeconfig=/home/master1/.kube/config get pods -A
```

Что проговорить:

- один `control-plane`
- три `worker`
- `Calico`
- `CoreDNS`
- namespaces `dev`, `qa`, `prod`, `monitoring`

### 2. Приложение в Kubernetes

На `cp1`:

```bash
kubectl --kubeconfig=/home/master1/.kube/config get deploy,svc,pods -n dev
kubectl --kubeconfig=/home/master1/.kube/config get deploy,svc,pods -n qa
kubectl --kubeconfig=/home/master1/.kube/config get deploy,svc,pods -n prod
```

Что проговорить:

- `dev` доступен снаружи через `NodePort`
- `qa` и `prod` развёрнуты как отдельные окружения
- приложение состоит из:
  - `api`
  - `worker`
  - `migration job`

### 3. Helm

На `cp1`:

```bash
helm ls -A
```

Что проговорить:

- один chart
- разные `values-dev.yaml`, `values-qa.yaml`, `values-prod.yaml`
- отдельные релизы по namespace

### 4. API

Из браузера:

- [http://10.211.55.9:30080/docs](http://10.211.55.9:30080/docs)
- [http://10.211.55.9:30080/health](http://10.211.55.9:30080/health)

Из терминала:

```bash
curl http://10.211.55.9:30080/health
curl http://10.211.55.9:30080/status
curl http://10.211.55.9:30080/status/1
```

### 5. Monitoring

В Grafana показать:

- папку `Uptime Monitor`
- dashboard `Kubernetes Overview`
- dashboard `Uptime Monitor App`

В Prometheus можно быстро показать targets:

```bash
curl -s 'http://10.211.55.3:9090/api/v1/targets' | jq '.data.activeTargets[] | {job: .labels.job, health: .health, scrapeUrl: .scrapeUrl}'
```

Что проговорить:

- `node_exporter` на всех 4 k8s-нодах
- `kube-state-metrics`
- scrape `dev` API
- alerts под Kubernetes

### 6. Alerts

В Prometheus показать rules:

```bash
curl -s 'http://10.211.55.3:9090/api/v1/rules' | jq '.data.groups[] | select(.name=="alerts.yml")'
```

Какие alert’ы есть:

- `KubernetesNodeExporterDown`
- `KubernetesNodeNotReady`
- `KubernetesPodCrashLooping`
- `KubernetesDeploymentReplicasMismatch`

## Негативный сценарий

Самый удобный сценарий для показа:

сломать образ `qa` API и показать alert `KubernetesDeploymentReplicasMismatch`.

### Сломать

```bash
kubectl --kubeconfig=/home/master1/.kube/config -n qa set image deployment/uptime-monitor-api api=ghcr.io/l4ty5h3v/uptime-monitor:does-not-exist
kubectl --kubeconfig=/home/master1/.kube/config -n qa delete pod -l app.kubernetes.io/component=api
kubectl --kubeconfig=/home/master1/.kube/config -n qa get pods -w
```

Потом показать:

```bash
curl -s 'http://10.211.55.3:9090/api/v1/query?query=ALERTS{alertname="KubernetesDeploymentReplicasMismatch",namespace="qa"}' | jq .
```

Или открыть rule/graph в Prometheus UI.

### Восстановить

```bash
kubectl --kubeconfig=/home/master1/.kube/config -n qa set image deployment/uptime-monitor-api api=ghcr.io/l4ty5h3v/uptime-monitor:dev
kubectl --kubeconfig=/home/master1/.kube/config rollout status deployment/uptime-monitor-api -n qa
```

## Если спросят про архитектуру

Короткий ответ:

- `10.211.55.3` — внешний stateful host:
  - PostgreSQL
  - Redis + Sentinel
  - Prometheus
  - Grafana
- `10.211.55.9` — `control-plane`
- `10.211.55.6`, `10.211.55.7`, `10.211.55.10` — `workers`
- приложение развёрнуто в Kubernetes
- данные остаются во внешних сервисах

## Если спросят про CI/CD

Показать файл:

- [docs/kubernetes-cicd-runbook.md](/Users/nikolay/.codex/worktrees/67e9/uptime-monitor-infra/docs/kubernetes-cicd-runbook.md)

Что проговорить:

- workflow собирает image
- пушит в `GHCR`
- запускает `helm upgrade --install`
- ждёт rollout
- поддерживает `dev`, `qa`, `prod`

## Минимальный маршрут, если времени мало

Если тебе дают мало времени, показывай только:

1. `kubectl get nodes`
2. `kubectl get pods -A`
3. `helm ls -A`
4. `http://10.211.55.9:30080/docs`
5. Grafana `Kubernetes Overview`
6. один alert rule
7. негативный сценарий в `qa`

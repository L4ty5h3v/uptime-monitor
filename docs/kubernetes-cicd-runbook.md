# Kubernetes CI/CD Runbook

Этот runbook нужен для первого живого прогона workflow
[.github/workflows/kubernetes-deploy.yml](/Users/nikolay/.codex/worktrees/67e9/uptime-monitor-infra/.github/workflows/kubernetes-deploy.yml).

## Что уже ожидает workflow

Workflow умеет:

- собрать Docker image
- запушить image в `GHCR`
- выполнить `helm lint`
- сделать `helm upgrade --install`
- дождаться rollout `api` и `worker`
- вывести состояние ресурсов в namespace

Pipeline работает на ветке `kubernetes` и поддерживает:

- автозапуск в `dev` по `push`
- ручной запуск в `dev`, `qa`, `prod` через `workflow_dispatch`

## Что нужно подготовить на self-hosted runner

На runner должны быть:

- Docker daemon
- доступ в интернет до `ghcr.io`
- сетевой доступ до Kubernetes API `10.211.55.9:6443`
- возможность записать файл в `~/.kube/config`

Минимальная проверка на runner:

```bash
docker info
curl -k https://10.211.55.9:6443/version
```

## Какие GitHub Secrets нужны

Нужен минимум один secret:

- `KUBECONFIG_B64`

`GITHUB_TOKEN` workflow получает автоматически.

Если registry/image станут приватными и kubelet не сможет тянуть образ из `GHCR`,
дополнительно понадобится `imagePullSecret` в Kubernetes, но сейчас это не обязательно.

## Как получить KUBECONFIG_B64

На `cp1`:

```bash
base64 -w 0 /home/master1/.kube/config
```

Если `base64 -w 0` недоступен:

```bash
base64 /home/master1/.kube/config | tr -d '\n'
```

Дальше:

1. открыть репозиторий в GitHub
2. `Settings -> Secrets and variables -> Actions`
3. создать secret `KUBECONFIG_B64`
4. вставить туда полученную base64-строку

## Как зарегистрировать self-hosted runner

На Ubuntu-хосте runner:

```bash
sudo apt update
sudo apt install -y curl tar git jq docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Потом в GitHub:

1. `Settings -> Actions -> Runners`
2. `New self-hosted runner`
3. выбрать Linux и нужную архитектуру
4. выполнить показанные GitHub команды `config.sh`
5. установить runner как сервис

Обычно это выглядит так:

```bash
mkdir -p ~/actions-runner
cd ~/actions-runner
curl -L -o actions-runner.tar.gz <RUNNER_TARBALL_URL>
tar xzf actions-runner.tar.gz
./config.sh --url https://github.com/<owner>/<repo> --token <token> --name uptime-k8s-runner
sudo ./svc.sh install
sudo ./svc.sh start
```

## Как запускать pipeline

### Автоматически в `dev`

Любой `push` в ветку `kubernetes` запускает:

- build
- push
- deploy в namespace `dev`

### Ручной запуск

В GitHub:

1. `Actions`
2. `Kubernetes deploy pipeline`
3. `Run workflow`
4. выбрать:
   - `dev`
   - `qa`
   - `prod`

## Что считать успешным прогоном

Успех — это когда workflow:

- собрал image
- запушил image в `GHCR`
- прошёл `helm lint`
- выполнил `helm upgrade --install`
- дождался `rollout status` для:
  - `deployment/uptime-monitor-api`
  - `deployment/uptime-monitor-worker`

И в конце показывает живые ресурсы:

```bash
kubectl get pods,svc,deploy -n <namespace>
helm status uptime-monitor -n <namespace>
```

## Быстрые post-deploy проверки

Для `dev`:

```bash
curl http://10.211.55.9:30080/health
curl http://10.211.55.9:30080/status
```

Для всех окружений:

```bash
kubectl get pods -n dev
kubectl get pods -n qa
kubectl get pods -n prod
helm ls -A
```

## Типичные причины падения

### Runner не подхватился

Проверить:

```bash
systemctl status actions.runner.*
docker info
```

### Не проходит deploy в кластер

Проверить:

```bash
kubectl --kubeconfig=/home/master1/.kube/config get nodes
kubectl get pods -A
```

### Pod не стартует из-за образа

Проверить:

```bash
kubectl describe pod -n <namespace> <pod-name>
kubectl logs -n <namespace> <pod-name>
```

### Не проходит migration job

Проверить:

```bash
kubectl get jobs -n <namespace>
kubectl logs job/uptime-monitor-migrate -n <namespace>
```

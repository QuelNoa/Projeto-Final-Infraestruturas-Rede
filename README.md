# Arquitetura Resiliente para Microsserviços Críticos  
**Mitigação de DoS e Auto-Recuperação em Kubernetes**

## Visão geral

Este repositório contém a implementação e os artefactos de um projeto académico cujo objetivo é **demonstrar resiliência operacional em microsserviços críticos**, recorrendo exclusivamente a primitivas nativas de Kubernetes.

A solução não tenta evitar falhas, mas **assume a sua inevitabilidade** e foca-se em:
- deteção rápida,
- contenção do impacto,
- recuperação automática e previsível,

avaliadas através de métricas objetivas como **MTTD**, **MTTR** e **RTO**.

O sistema foi concebido para ser **reproduzível**, **observável** e **explicável**, privilegiando causalidade clara em detrimento de cenários artificiais ou excessivamente complexos.

---

## Arquitetura resumida

A arquitetura é composta por três microsserviços principais:

| Serviço | Função | Réplicas |
|-------|--------|----------|
| API | Lógica principal + endpoints críticos | 3 |
| Auth | Autenticação interna (dependência da API) | 1 |
| Dashboard | Interface visual | 1 |

Camadas principais:
- **Ingress NGINX** com TLS e rate limiting (primeira linha de defesa DoS)
- **Services Kubernetes** como ponto lógico de acesso
- **Deployments** com múltiplas réplicas
- **Readiness/Liveness probes**
- **Horizontal Pod Autoscaler (HPA)**
- **NetworkPolicies** em modo deny-by-default
- **TLS interno** entre API e Auth

---

## Incidentes simulados

Foram executados **três tipos de incidentes controlados**, cada um validando uma propriedade distinta da arquitetura:

1. **DoS controlado**
   - Carga CPU-bound aplicada à API
   - Objetivo: observar degradação controlada sem falha funcional

2. **Falha de instância (kill de pod da API)**
   - Eliminação abrupta de um pod
   - Objetivo: validar redundância e self-healing invisível ao cliente

3. **Falha de rede interna (API → Auth)**
   - Bloqueio temporário via NetworkPolicy
   - Objetivo: demonstrar degradação parcial e confinamento do impacto

---

## Metodologia e métricas

Cada execução (“run”) segue uma sequência determinística:
1. Baseline funcional
2. DoS
3. Kill de pod
4. Falha de rede
5. Recuperação

A monitorização é feita do **ponto de vista do cliente**, com pedidos periódicos aos endpoints:
- `/ping` (estado geral do serviço)
- `/secure-data` (funcionalidade dependente de Auth)

Para cada pedido são registados:
- timestamp,
- endpoint,
- código HTTP,
- latência,
- sucesso/falha.

As métricas são calculadas com os seguintes critérios:
- **MTTD**: tempo até à primeira falha observável
- **MTTR**: tempo entre a falha e a recuperação estável
- **RTO**: tempo total de indisponibilidade
- **Recuperação estável**: 3 respostas consecutivas bem-sucedidas

---

## Artefactos gerados

Cada run produz automaticamente evidência, incluindo:

- `http_metrics.csv` — métricas HTTP de alta resolução
- `metrics.json` / `metrics.md` — MTTD, MTTR, RTO por incidente
- `dos_k6_summary.json` — resumo de carga DoS
- `events.log` / `commands.log` — timeline de incidentes
- `report.html` — relatório visual consolidado




---
## Como reproduzir (resumo)



Requisitos:
- Docker
- Kubernetes local (k3d / kind / minikube)
- kubectl
- k6

Passos gerais:
1. Criar cluster local
2. Aplicar manifests Kubernetes
3. Iniciar monitorização
4. Executar scripts de incidentes
5. Analisar artefactos gerados

---

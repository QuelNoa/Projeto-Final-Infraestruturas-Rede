# Métricas de Resiliência — demo_20260121_074144

- Diretoria do run: `/home/ariana/projetos/resilient-microservices/results/demo_20260121_074144`
- Recuperação estável: **3 OK consecutivos**
- Janela pós-incidente: **30s**
- RPO: **0 (stateless/NA)**

## Baseline
- FIRST_FAILURE antes do 1º incidente: **—**
- Nota: Baseline FIRST_FAILURE só é considerado se ocorrer antes do 1º INCIDENT_START.

## Incidentes (MTTD / MTTR / RTO)
### dos
- **/ping**
  - Início: 2026-01-21T07:41:47+00:00
  - Fim: 2026-01-21T07:43:09+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.
- **/secure-data**
  - Início: 2026-01-21T07:41:47+00:00
  - Fim: 2026-01-21T07:43:09+00:00
  - FIRST_FAILURE: 2026-01-21T07:43:35+00:00
  - RECOVERED (estável): —
  - MTTD(s): 108.0
  - MTTR(s): -
  - RTO(s): -
  - Nota: Falha detetada, mas sem recuperação estável na janela.

### netfail
- **/ping**
  - Início: 2026-01-21T07:43:32+00:00
  - Fim: 2026-01-21T07:43:54+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.
- **/secure-data**
  - Início: 2026-01-21T07:43:32+00:00
  - Fim: 2026-01-21T07:43:54+00:00
  - FIRST_FAILURE: 2026-01-21T07:43:35+00:00
  - RECOVERED (estável): 2026-01-21T07:43:55+00:00
  - MTTD(s): 3.0
  - MTTR(s): 20.0
  - RTO(s): 23.0

## DoS (k6)
- http_reqs: **8994.0**
- p95: **542.48588635 ms**
- max: **2369.695102 ms**
- fonte: `/home/ariana/projetos/resilient-microservices/results/demo_20260121_074144/dos/k6_summary.json`

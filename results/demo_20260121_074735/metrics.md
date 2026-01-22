# Métricas de Resiliência — demo_20260121_074735

- Diretoria do run: `/home/ariana/projetos/resilient-microservices/results/demo_20260121_074735`
- Recuperação estável: **3 OK consecutivos**
- Janela pós-incidente: **30s**
- RPO: **0 (stateless/NA)**

## Baseline
- FIRST_FAILURE antes do 1º incidente: **—**
- Nota: Baseline FIRST_FAILURE só é considerado se ocorrer antes do 1º INCIDENT_START.

## Incidentes (MTTD / MTTR / RTO)
### dos
- **/ping**
  - Início: 2026-01-21T07:47:41+00:00
  - Fim: 2026-01-21T07:49:04+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.
- **/secure-data**
  - Início: 2026-01-21T07:47:41+00:00
  - Fim: 2026-01-21T07:49:04+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.

### netfail
- **/ping**
  - Início: 2026-01-21T07:49:59+00:00
  - Fim: 2026-01-21T07:50:19+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.
- **/secure-data**
  - Início: 2026-01-21T07:49:59+00:00
  - Fim: 2026-01-21T07:50:19+00:00
  - FIRST_FAILURE: 2026-01-21T07:50:00+00:00
  - RECOVERED (estável): 2026-01-21T07:50:20+00:00
  - MTTD(s): 1.0
  - MTTR(s): 20.0
  - RTO(s): 21.0

## DoS (k6)
- http_reqs: **13749.0**
- p95: **297.63017659999986 ms**
- max: **1853.084166 ms**
- fonte: `/home/ariana/projetos/resilient-microservices/results/demo_20260121_074735/dos/k6_summary.json`

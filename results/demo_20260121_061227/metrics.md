# Métricas de Resiliência — demo_20260121_061227

- Diretoria do run: `/home/ariana/projetos/resilient-microservices/results/demo_20260121_061227`
- Recuperação estável: **3 OK consecutivos**
- Janela pós-incidente: **30s**
- RPO: **0 (stateless/NA)**

## Baseline
- FIRST_FAILURE antes do 1º incidente: **—**
- Nota: Baseline FIRST_FAILURE só é considerado se ocorrer antes do 1º INCIDENT_START.

## Incidentes (MTTD / MTTR / RTO)
### dos
- **/ping**
  - Início: 2026-01-21T06:12:32+00:00
  - Fim: 2026-01-21T06:13:53+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.
- **/secure-data**
  - Início: 2026-01-21T06:12:32+00:00
  - Fim: 2026-01-21T06:13:53+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.

### netfail
- **/ping**
  - Início: 2026-01-21T06:14:37+00:00
  - Fim: 2026-01-21T06:14:58+00:00
  - FIRST_FAILURE: —
  - RECOVERED (estável): —
  - MTTD(s): -
  - MTTR(s): -
  - RTO(s): -
  - Nota: Sem falha detetada na janela do incidente.
- **/secure-data**
  - Início: 2026-01-21T06:14:37+00:00
  - Fim: 2026-01-21T06:14:58+00:00
  - FIRST_FAILURE: 2026-01-21T06:14:39+00:00
  - RECOVERED (estável): 2026-01-21T06:14:58+00:00
  - MTTD(s): 2.0
  - MTTR(s): 19.0
  - RTO(s): 21.0

## DoS (k6)
- http_reqs: **10635.0**
- p95: **387.16266369999994 ms**
- max: **1798.436315 ms**
- fonte: `/home/ariana/projetos/resilient-microservices/results/demo_20260121_061227/dos/k6_summary.json`

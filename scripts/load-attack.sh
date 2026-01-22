#!/usr/bin/env bash

TARGET="https://api.resilience.local/ping"

# Criando o arquivo de teste do k6
cat <<'EOF_INNER' > /tmp/k6-test.js
import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '2m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  http.get(__ENV.TARGET);
  sleep(0.1);
}
EOF_INNER

echo "Iniciando ataque de carga contra $TARGET (2 minutos)..."
k6 run /tmp/k6-test.js -e TARGET=$TARGET

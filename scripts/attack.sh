import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '20s', target: 10 }, // Aquecimento
    { duration: '40s', target: 100 }, // Ataque DoS (Requisito 5)
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    // Esperamos que > 50% dos pedidos falhem com 429 durante o ataque (mitigação ativa)
    'http_req_failed': ['rate > 0.1'], 
  },
};

export default function () {
  let res = http.get('https://api.resilience.local/work?n=50000', {
    tags: { name: 'DoS-Attack' },
    timeout: '5s'
  });
  
  // Verificamos se estamos a ser mitigados pelo Nginx (429) ou se o sistema ainda responde (200)
  check(res, {
    'is status 200 or 429': (r) => r.status === 200 || r.status === 429,
  });
  
  sleep(0.1);
}
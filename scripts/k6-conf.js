import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  vus: 50, // 50 utilizadores simultâneos
  duration: '30s',
  insecureSkipTLSVerify: true,
};

export default function () {
  http.get('https://api.resilience.local/ping');
}
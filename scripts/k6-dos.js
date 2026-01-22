import http from "k6/http";
import { sleep } from "k6";
import { Rate } from "k6/metrics";

export const rate_429 = new Rate("rate_429");
export const rate_5xx = new Rate("rate_5xx");
export const rate_timeout = new Rate("rate_timeout");

export const options = {
  insecureSkipTLSVerify: true,
  stages: [
    { duration: "15s", target: 10 },
    { duration: "45s", target: 80 },
    { duration: "15s", target: 0 },
  ],
  thresholds: {
    rate_429: ["rate<0.05"],       // queremos ver mitigação
    rate_5xx: ["rate<0.10"],       // 5xx não é “mitigação”, é “queda”
    rate_timeout: ["rate<0.20"],   // tolera algum
  },
};

export default function () {
  const url = "https://api.resilience.local/work?n=400000"; // <- baixa para estabilizar
  const res = http.get(url, { timeout: "20s" });

  rate_429.add(res.status === 429);
  rate_5xx.add(res.status >= 500);

  // status 0: falha de rede/timeout do lado do cliente
  rate_timeout.add(res.status === 0);

  if (res.status >= 500 || res.status === 0) {
    console.error(`err status=${res.status} url=/work`);
  }

  sleep(0.1);
}

/**
 * Spike test — ramps from 1 to 50 VUs to find breaking points.
 * Run: k6 run --env BASE_URL=http://localhost:8080 k6/spike.js
 * See k6/README.md for required env vars.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { acquireToken, bearerHeaders, BASE_URL } from "./helpers.js";

export const options = {
  stages: [
    { duration: "30s", target: 1 },
    { duration: "1m", target: 10 },
    { duration: "30s", target: 50 },
    { duration: "1m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(99)<5000"],
  },
};

export function setup() {
  const u = __ENV.K6_USER;
  const p = __ENV.K6_PASS;
  if (!u || !p) throw new Error("Set K6_USER and K6_PASS env vars");
  return { token: acquireToken(u, p) };
}

export default function (data) {
  const h = bearerHeaders(data.token);

  const d = http.get(`${BASE_URL}/api/v1/dashboard`, h);
  check(d, { "dashboard ok": (r) => r.status === 200 });

  const sk = http.get(`${BASE_URL}/api/v1/skills`, h);
  check(sk, { "skills ok": (r) => r.status === 200 });

  sleep(1);
}

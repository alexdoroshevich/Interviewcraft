/**
 * Smoke test — 1 VU, 30 seconds.
 * Verifies all critical endpoints respond before running load tests.
 *
 * Usage:
 *   k6 run --env BASE_URL=http://localhost:8080 --env K6_USER=... --env K6_PASS=... k6/smoke.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { acquireToken, bearerHeaders, BASE_URL } from "./helpers.js";

export const options = {
  vus: 1,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
  },
};

export function setup() {
  const user = __ENV.K6_USER || "k6smoke@test.local";
  const pass = __ENV.K6_PASS || "K6SmokePw!1";
  const token = acquireToken(user, pass);
  return { token };
}

export default function (data) {
  const h = bearerHeaders(data.token);

  // Health check
  const health = http.get(`${BASE_URL}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  // Dashboard — most-used read endpoint
  const dashboard = http.get(`${BASE_URL}/api/v1/dashboard`, h);
  check(dashboard, { "dashboard 200": (r) => r.status === 200 });

  // Sessions list
  const sessions = http.get(`${BASE_URL}/api/v1/sessions`, h);
  check(sessions, { "sessions 200": (r) => r.status === 200 });

  // Skills
  const skills = http.get(`${BASE_URL}/api/v1/skills`, h);
  check(skills, { "skills 200": (r) => r.status === 200 });

  // Skill benchmark
  const benchmark = http.get(`${BASE_URL}/api/v1/skills/benchmark`, h);
  check(benchmark, { "benchmark 200": (r) => r.status === 200 });

  // Profile
  const profile = http.get(`${BASE_URL}/api/v1/profile`, h);
  check(profile, { "profile 200": (r) => r.status === 200 });

  // Memory context
  const memory = http.get(`${BASE_URL}/api/v1/settings/memory`, h);
  check(memory, { "memory 200|404": (r) => r.status === 200 || r.status === 404 });

  sleep(1);
}

/**
 * Baseline load test — 10 VUs, 2 minutes.
 * Run: k6 run --env BASE_URL=http://localhost:8080 k6/load.js
 * Env vars required: TEST_EMAIL, TEST_CREDENTIAL (see k6/README.md)
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Trend } from "k6/metrics";
import { acquireToken, bearerHeaders, BASE_URL } from "./helpers.js";

const dashboardLatency = new Trend("dashboard_latency", true);
const sessionsLatency = new Trend("sessions_latency", true);
const skillsLatency = new Trend("skills_latency", true);
const scoringLatency = new Trend("scoring_get_latency", true);

export const options = {
  vus: 10,
  duration: "2m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(50)<200", "p(95)<800", "p(99)<2000"],
    dashboard_latency: ["p(95)<600"],
    sessions_latency: ["p(95)<500"],
    skills_latency: ["p(95)<400"],
    scoring_get_latency: ["p(95)<800"],
  },
};

export function setup() {
  const email = __ENV.TEST_EMAIL;
  const cred = __ENV.TEST_CREDENTIAL;
  if (!email || !cred) {
    throw new Error("Set TEST_EMAIL and TEST_CREDENTIAL env vars");
  }
  return { token: acquireToken(email, cred) };
}

export default function (data) {
  const h = bearerHeaders(data.token);

  group("read_path", () => {
    const d = http.get(`${BASE_URL}/api/v1/dashboard`, h);
    check(d, { "dashboard ok": (r) => r.status === 200 });
    dashboardLatency.add(d.timings.duration);

    const s = http.get(`${BASE_URL}/api/v1/sessions`, h);
    check(s, { "sessions ok": (r) => r.status === 200 });
    sessionsLatency.add(s.timings.duration);

    const sk = http.get(`${BASE_URL}/api/v1/skills`, h);
    check(sk, { "skills ok": (r) => r.status === 200 });
    skillsLatency.add(sk.timings.duration);

    const bm = http.get(`${BASE_URL}/api/v1/skills/benchmark`, h);
    check(bm, { "benchmark ok": (r) => r.status === 200 });
  });

  group("profile_path", () => {
    const p = http.get(`${BASE_URL}/api/v1/profile`, h);
    check(p, { "profile ok": (r) => r.status === 200 });

    const me = http.get(`${BASE_URL}/api/v1/auth/me`, h);
    check(me, { "me ok": (r) => r.status === 200 });
  });

  group("session_detail", () => {
    const listRes = http.get(`${BASE_URL}/api/v1/sessions`, h);
    if (listRes.status === 200) {
      const sessions = listRes.json();
      if (Array.isArray(sessions) && sessions.length > 0) {
        const sid = sessions[0].id;
        const detail = http.get(`${BASE_URL}/api/v1/sessions/${sid}`, h);
        check(detail, { "session detail ok": (r) => r.status === 200 });
        const score = http.get(`${BASE_URL}/api/v1/sessions/${sid}/score`, h);
        check(score, { "score ok": (r) => r.status === 200 || r.status === 404 });
        scoringLatency.add(score.timings.duration);
      }
    }
  });

  sleep(Math.random() * 2 + 1);
}

/**
 * Shared helpers for InterviewCraft k6 load tests.
 * Handles token acquisition and common request headers.
 */

import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";

/**
 * Acquire a JWT token for load test VUs.
 * Tries login first; falls back to register then login.
 * Call in setup() — pass the returned token to default() via data param.
 */
export function acquireToken(testEmail, testCredential) {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: testEmail, password: testCredential }),
    { headers: { "Content-Type": "application/json" } }
  );

  if (loginRes.status === 200) {
    return loginRes.json("access_token");
  }

  // First run: register the test account
  const registerRes = http.post(
    `${BASE_URL}/api/v1/auth/register`,
    JSON.stringify({ email: testEmail, password: testCredential }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(registerRes, {
    "test account created": (r) => r.status === 201 || r.status === 200,
  });

  const loginRes2 = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: testEmail, password: testCredential }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(loginRes2, { "token acquired": (r) => r.status === 200 });
  return loginRes2.json("access_token");
}

/** Standard headers for authenticated requests. */
export function bearerHeaders(token) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };
}

export { BASE_URL };

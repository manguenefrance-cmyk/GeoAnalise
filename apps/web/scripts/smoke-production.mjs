import assert from "node:assert/strict";

const origin = "http://127.0.0.1:3000";
let health;
for (let attempt = 0; attempt < 30; attempt++) {
  try {
    const response = await fetch(`${origin}/api/healthz`, {
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) {
      health = await response.json();
      break;
    }
  } catch {
    // Allow the freshly started Next.js process to become ready.
  }
  await new Promise((resolve) => setTimeout(resolve, 1000));
}
assert.equal(health?.status, "ok", "Web-to-API proxy must reach the healthy API");
assert.equal(health.mode, "production", "The online stack must use production authentication");

const home = await fetch(origin, { signal: AbortSignal.timeout(10000) });
assert.equal(home.status, 200);
assert.match(await home.text(), /ARCAMBE/);

for (const headers of [{}, { Authorization: "Bearer test:demo" }]) {
  const response = await fetch(`${origin}/api/v1/projects`, {
    headers,
    signal: AbortSignal.timeout(10000),
  });
  assert.equal(response.status, 401, "Missing credentials and local test tokens must be refused");
}
console.log("Production containers passed: web, API proxy, database readiness and authentication guards.");

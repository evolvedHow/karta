import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";

import { createRuntimeServer, tokenMatches } from "../src/server.js";

/** Runtime configuration used by the HTTP tests. */
const CONFIG = {
  host: "127.0.0.1",
  port: 0,
  internalToken: "test-internal-token",
  margaBaseUrl: "http://127.0.0.1:8010/v1",
};

test("tokenMatches rejects missing, wrong and empty tokens", () => {
  assert.equal(tokenMatches("test-internal-token", CONFIG.internalToken), true);
  assert.equal(tokenMatches("wrong", CONFIG.internalToken), false);
  assert.equal(tokenMatches(undefined, CONFIG.internalToken), false);
  assert.equal(tokenMatches("", CONFIG.internalToken), false);
});

test("health is public and execution requires the internal token", async () => {
  const server = createRuntimeServer(CONFIG);
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = (server.address() as AddressInfo).port;
  try {
    const health = await fetch(`http://127.0.0.1:${port}/health`);
    assert.equal(health.status, 200);
    assert.equal((await health.json() as { status: string }).status, "ok");

    const unauthenticated = await fetch(`http://127.0.0.1:${port}/v1/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    assert.equal(unauthenticated.status, 401);

    const badBody = await fetch(`http://127.0.0.1:${port}/v1/execute`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Karta-Internal-Token": CONFIG.internalToken,
      },
      body: "{}",
    });
    assert.equal(badBody.status, 400);
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error === undefined ? resolve() : reject(error))),
    );
  }
});

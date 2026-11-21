import assert from "node:assert/strict";
import test from "node:test";

import { assistantText } from "../src/adapter.js";
import { loadConfig } from "../src/config.js";

test("loadConfig reads environment values and rejects blanks", () => {
  const config = loadConfig({
    KARTA_SPIKE_MARGA_URL: "http://127.0.0.1:8011/v1",
    KARTA_SPIKE_MODEL: "mock-tool",
    KARTA_SPIKE_API_KEY: "spike-placeholder",
    KARTA_SPIKE_TENANT_ID: "tenant-a",
    KARTA_SPIKE_TASK_ID: "task-1",
    OTEL_EXPORTER_OTLP_ENDPOINT: "http://127.0.0.1:4318",
    KARTA_SPIKE_RESULT_PATH: "artifacts/pi-result.json",
  });
  assert.equal(config.tenantId, "tenant-a");
  assert.equal(config.taskId, "task-1");
  assert.throws(() => loadConfig({ KARTA_SPIKE_TENANT_ID: "   " }), /must not be blank/);
});

test("assistantText concatenates only assistant text blocks", () => {
  const transcript: readonly unknown[] = [
    { role: "user", content: [{ type: "text", text: "prompt" }] },
    { role: "assistant", content: [{ type: "text", text: "Hello " }, { type: "thinking", text: "hidden" }] },
    { role: "assistant", content: [{ type: "text", text: "world" }] },
  ];
  assert.equal(assistantText(transcript), "Hello world");
});

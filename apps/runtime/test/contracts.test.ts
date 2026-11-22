import assert from "node:assert/strict";
import { test } from "node:test";

import { isRecord, parseExecutionRequest, parseProfile } from "../src/contracts.js";

/** Build a minimal valid execution request body. */
function validBody(): Record<string, unknown> {
  return {
    task_id: "task-1",
    tenant_id: "tenant-a",
    session_id: "task-1",
    prompt: "Create a file",
    workspace_path: "/tmp/workspace",
    profile: {
      id: "coding",
      version: "1.0.0",
      instructions: "Work in the workspace",
      tools: ["read_file", "write_file"],
      model_policy: { strong: "strong" },
      limits: { max_iterations: 5, max_tool_calls: 5, max_execution_minutes: 5 },
    },
    marga_base_url: "http://127.0.0.1:8010/v1",
    model: "strong",
    api_key: "internal-placeholder",
    correlation_id: "corr-1",
    limits: { max_iterations: 5, max_tool_calls: 5, max_execution_minutes: 5 },
  };
}

test("parseExecutionRequest accepts a valid contract", () => {
  const parsed = parseExecutionRequest(validBody());
  assert.equal(parsed.task_id, "task-1");
  assert.equal(parsed.profile.model_policy.strong, "strong");
  assert.equal(parsed.limits.max_tool_calls, 5);
});

test("parseExecutionRequest rejects missing tenant and malformed limits", () => {
  const missingTenant = validBody();
  delete missingTenant["tenant_id"];
  assert.throws(() => parseExecutionRequest(missingTenant), /tenant_id/);

  const badLimits = validBody();
  badLimits["limits"] = { max_iterations: 0, max_tool_calls: 5, max_execution_minutes: 5 };
  assert.throws(() => parseExecutionRequest(badLimits), /max_iterations/);
});

test("parseProfile uses profile limits when request limits are absent", () => {
  const body = validBody();
  delete body["limits"];
  const parsed = parseExecutionRequest(body);
  assert.equal(parsed.limits.max_iterations, 5);
  assert.deepEqual(parseProfile(body["profile"]).tools, ["read_file", "write_file"]);
});

test("isRecord rejects arrays, null and primitives", () => {
  assert.equal(isRecord({}), true);
  assert.equal(isRecord([]), false);
  assert.equal(isRecord(null), false);
  assert.equal(isRecord("value"), false);
});

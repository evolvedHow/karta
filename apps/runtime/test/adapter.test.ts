import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { createServer, type Server } from "node:http";
import { test } from "node:test";

import { assistantText, KartaRuntimeAdapter, safeErrorMessage } from "../src/adapter.js";
import type { ExecutionRequest } from "../src/contracts.js";

/**
 * Build one OpenAI-compatible streaming chunk.
 *
 * @param id - Completion identifier.
 * @param model - Model echoed from the request.
 * @param delta - Incremental assistant message.
 * @param finish - Optional finish reason.
 * @param usage - Optional token usage.
 * @returns Chunk payload.
 */
function chunk(
  id: string,
  model: string,
  delta: Record<string, unknown>,
  finish?: string,
  usage?: Record<string, number>,
): Record<string, unknown> {
  return {
    id,
    object: "chat.completion.chunk",
    created: 1,
    model,
    choices: [{ index: 0, delta, finish_reason: finish ?? null }],
    ...(usage === undefined ? {} : { usage }),
  };
}

/**
 * Encode a payload as an SSE data frame.
 *
 * @param payload - Chunk payload.
 * @returns Encoded frame.
 */
function frame(payload: Record<string, unknown>): string {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

/**
 * Start a deterministic OpenAI-compatible mock Marga endpoint.
 *
 * The first completion requests a `write_file` tool call; the second returns
 * a streamed final answer. This mirrors the Milestone 0 wire format.
 *
 * @returns Listening server.
 */
async function startMockMarga(): Promise<Server> {
  const server = createServer((request, response) => {
    void (async () => {
      const chunks: Buffer[] = [];
      for await (const piece of request) {
        chunks.push(Buffer.isBuffer(piece) ? piece : Buffer.from(piece as string));
      }
      const body = JSON.parse(Buffer.concat(chunks).toString("utf8")) as {
        model?: string;
        messages?: Array<{ role?: string }>;
      };
      const model = body.model ?? "strong";
      const id = "chatcmpl-mock";
      const hasToolResult = (body.messages ?? []).some((message) => message.role === "tool");
      const frames: string[] = [];
      if (hasToolResult) {
        for (const piece of ["Wrote ", "the file."]) {
          frames.push(frame(chunk(id, model, { content: piece })));
        }
        frames.push(
          frame(chunk(id, model, {}, "stop", { prompt_tokens: 34, completion_tokens: 5, total_tokens: 39 })),
        );
      } else {
        frames.push(
          frame(
            chunk(id, model, {
              role: "assistant",
              tool_calls: [
                {
                  index: 0,
                  id: "call_write_1",
                  type: "function",
                  function: { name: "write_file", arguments: "" },
                },
              ],
            }),
          ),
        );
        for (const piece of ['{"path":', '"note.txt",', '"content":', '"hello kartā"}']) {
          frames.push(
            frame(
              chunk(id, model, {
                tool_calls: [{ index: 0, function: { arguments: piece } }],
              }),
            ),
          );
        }
        frames.push(
          frame(chunk(id, model, {}, "tool_calls", { prompt_tokens: 24, completion_tokens: 12, total_tokens: 36 })),
        );
      }
      frames.push("data: [DONE]\n\n");
      response.writeHead(200, { "Content-Type": "text/event-stream" });
      response.end(frames.join(""));
    })();
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return server;
}

test("Pi adapter executes a workspace tool call through mock Marga", async () => {
  const workspace = await mkdtemp(path.join(tmpdir(), "karta-adapter-"));
  const server = await startMockMarga();
  const port = (server.address() as AddressInfo).port;
  const limits = { max_iterations: 10, max_tool_calls: 10, max_execution_minutes: 5 };
  const request: ExecutionRequest = {
    task_id: "task-1",
    tenant_id: "tenant-a",
    session_id: "task-1",
    prompt: "Write a note",
    workspace_path: workspace,
    profile: {
      id: "coding",
      version: "1.0.0",
      instructions: "Use write_file and then report what you did.",
      tools: ["read_file", "write_file", "list_files"],
      model_policy: { strong: "strong" },
      limits,
    },
    marga_base_url: `http://127.0.0.1:${port}/v1`,
    model: "strong",
    api_key: "placeholder",
    correlation_id: "corr-1",
    limits,
  };
  try {
    const result = await new KartaRuntimeAdapter().execute(request);
    assert.equal(result.status, "completed");
    assert.equal(result.final_text, "Wrote the file.");
    assert.equal(result.usage.total_tokens, 39);
    assert.equal(await readFile(path.join(workspace, "note.txt"), "utf8"), "hello kartā");

    const types = result.events.map((event) => event.event_type);
    assert.ok(types.includes("tool.started"));
    assert.ok(types.includes("tool.completed"));
    assert.ok(types.includes("message.delta"));
    assert.deepEqual(
      result.events.map((event) => event.sequence),
      result.events.map((_event, index) => index + 1),
    );
    for (const event of result.events) {
      assert.equal(event.tenant_id, "tenant-a");
      assert.equal(event.task_id, "task-1");
      assert.equal(event.correlation_id, "corr-1");
    }
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error === undefined ? resolve() : reject(error))),
    );
  }
});

test("helpers normalize Pi transcripts and redact errors", () => {
  assert.equal(
    assistantText([
      { role: "user", content: [{ type: "text", text: "hi" }] },
      { role: "assistant", content: [{ type: "text", text: "hello" }] },
    ]),
    "hello",
  );
  assert.equal(
    safeErrorMessage(new Error("failed with Bearer abc123 at http://127.0.0.1:9/v1")),
    "failed with Bearer [redacted] at [url]",
  );
});

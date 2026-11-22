/** HTTP entry point exposing the Pi runtime execution contract. */

import { createHash, timingSafeEqual } from "node:crypto";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import type { Server } from "node:http";

import { KartaRuntimeAdapter } from "./adapter.js";
import { loadConfig, type RuntimeConfig } from "./config.js";
import { parseExecutionRequest } from "./contracts.js";

/** Maximum accepted request body size in bytes. */
const MAX_BODY_BYTES = 1024 * 1024;

/**
 * Send a JSON response.
 *
 * @param response - HTTP response object.
 * @param status - HTTP status code.
 * @param body - JSON-serializable response body.
 */
function sendJson(response: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(payload),
  });
  response.end(payload);
}

/**
 * Read a bounded request body as UTF-8 text.
 *
 * @param request - Incoming request.
 * @returns Request body text.
 * @throws Error when the body is too large or a read error occurs.
 */
async function readBody(request: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  let length = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk as string);
    length += buffer.length;
    if (length > MAX_BODY_BYTES) {
      throw new Error("request body too large");
    }
    chunks.push(buffer);
  }
  return Buffer.concat(chunks).toString("utf8");
}

/**
 * Compare the internal token using hashed constant-time equality.
 *
 * @param supplied - Token from the request header.
 * @param expected - Configured shared secret.
 * @returns True when the tokens match.
 */
export function tokenMatches(supplied: string | undefined, expected: string): boolean {
  if (supplied === undefined || supplied.length === 0) {
    return false;
  }
  const left = createHash("sha256").update(supplied).digest();
  const right = createHash("sha256").update(expected).digest();
  return timingSafeEqual(left, right);
}

/**
 * Create the Pi runtime HTTP server.
 *
 * @param config - Validated runtime configuration.
 * @param adapter - Execution adapter, injectable for tests.
 * @returns Configured HTTP server.
 */
export function createRuntimeServer(
  config: RuntimeConfig,
  adapter: KartaRuntimeAdapter = new KartaRuntimeAdapter(),
): Server {
  return createServer((request, response) => {
    void (async () => {
      const path = (request.url ?? "").split("?")[0];
      if (request.method === "GET" && path === "/health") {
        sendJson(response, 200, { status: "ok", version: "0.1.0" });
        return;
      }
      const supplied = request.headers["x-karta-internal-token"];
      const token = Array.isArray(supplied) ? supplied[0] : supplied;
      if (!tokenMatches(token, config.internalToken)) {
        sendJson(response, 401, { error: { code: "unauthorized", message: "Internal token required" } });
        return;
      }
      if (request.method !== "POST" || path !== "/v1/execute") {
        sendJson(response, 404, { error: { code: "not_found", message: "Unknown endpoint" } });
        return;
      }
      try {
        const raw = await readBody(request);
        const executionRequest = parseExecutionRequest(JSON.parse(raw));
        const result = await adapter.execute(executionRequest);
        sendJson(response, 200, result);
      } catch (error) {
        const message = error instanceof Error ? error.message : "invalid request";
        const status = message.includes("body too large") ? 413 : 400;
        sendJson(response, status, { error: { code: "invalid_request", message } });
      }
    })();
  });
}

/**
 * Start the runtime service in the current process.
 *
 * @returns The listening HTTP server.
 */
export function startRuntimeServer(): Server {
  const config = loadConfig();
  const server = createRuntimeServer(config);
  server.listen(config.port, config.host, () => {
    process.stdout.write(`kartā runtime listening on http://${config.host}:${config.port}\n`);
  });
  return server;
}

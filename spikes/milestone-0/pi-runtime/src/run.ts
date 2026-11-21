import { mkdir, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { trace } from "@opentelemetry/api";
import { Openlit } from "openlit";

import { KartaSpikeRuntime } from "./adapter.js";
import { loadConfig } from "./config.js";

const TASK_PROMPT = "Add 2 and 2 using the add tool, then report the result.";

/** Subset of the SDK tracer provider used to drain spans before exit. */
interface FlushableProvider {
  /** Wait for queued spans to reach the configured exporter. */
  forceFlush(): Promise<void>;
  /** Stop span processing and release exporter resources. */
  shutdown(): Promise<void>;
}

/**
 * Narrow the global tracer provider to one exposing lifecycle methods.
 *
 * @param provider - Value returned by the OpenTelemetry API.
 * @returns True when the provider can be flushed and shut down.
 */
function isFlushableProvider(provider: unknown): provider is FlushableProvider {
  if (typeof provider !== "object" || provider === null) {
    return false;
  }
  const candidate = provider as { forceFlush?: unknown; shutdown?: unknown };
  return typeof candidate.forceFlush === "function" && typeof candidate.shutdown === "function";
}

/**
 * Flush and shut down the OpenLIT tracer provider.
 *
 * OpenLIT uses a simple span processor when `disableBatch` is set. The HTTP
 * export is still asynchronous, so a short-lived CLI process must drain it
 * explicitly or the final span is lost at exit.
 *
 * @returns Promise resolving when the provider has been shut down.
 */
async function flushTelemetry(): Promise<void> {
  const provider: unknown = trace.getTracerProvider();
  if (!isFlushableProvider(provider)) {
    return;
  }
  await provider.forceFlush();
  await provider.shutdown();
}

/**
 * Initialize OpenLIT and execute the spike task once.
 *
 * @returns Promise resolving when the result artifact has been written.
 */
async function main(): Promise<void> {
  const config = loadConfig();
  Openlit.init({
    applicationName: "karta-runtime-spike",
    environment: "spike",
    otlpEndpoint: config.otlpEndpoint,
    disableBatch: true,
    disableMetrics: true,
    disableEvents: true,
  });
  // OpenLIT registers the global W3C propagator during init; adding another
  // one here would log a duplicate-registration error.

  const runtime = new KartaSpikeRuntime(config);
  const result = await runtime.executeTask(TASK_PROMPT);
  await mkdir(dirname(config.resultPath), { recursive: true });
  await writeFile(config.resultPath, `${JSON.stringify({ task: TASK_PROMPT, ...result }, null, 2)}\n`);
  await flushTelemetry();
  console.log(JSON.stringify({ text: result.text, executedTools: result.executedTools, streamingDeltaCount: result.streamingDeltaCount }));
}

await main();

import { context, propagation } from "@opentelemetry/api";
import {
  Agent,
  type AgentEvent,
  type AgentTool,
  type AgentToolResult,
  type StreamFn,
} from "@earendil-works/pi-agent-core";
import type { Model } from "@earendil-works/pi-ai";
import { streamSimple } from "@earendil-works/pi-ai/compat";
import { startTrace } from "openlit";

import type { RuntimeConfig } from "./config.js";

/** Parameters accepted by the tool used to prove tool calling. */
export interface AddParams {
  /** First operand. */
  a: number;
  /** Second operand. */
  b: number;
}

/**
 * Narrow unknown tool arguments to the `add` parameter shape.
 *
 * @param value - Raw arguments supplied by the model.
 * @returns Validated operands, or undefined when the shape is wrong.
 */
export function asAddParams(value: unknown): AddParams | undefined {
  if (typeof value !== "object" || value === null) {
    return undefined;
  }
  const candidate = value as { a?: unknown; b?: unknown };
  if (typeof candidate.a !== "number" || typeof candidate.b !== "number") {
    return undefined;
  }
  return { a: candidate.a, b: candidate.b };
}

/** Structured details returned by the spike tool. */
export interface ToolDetails {
  /** Tool name that produced the details. */
  toolName: string;
  /** Sum computed by the tool. */
  sum: number;
}

/** Platform-level event emitted by the spike adapter. */
export interface SpikeEvent {
  /** Monotonic event sequence within the task. */
  sequence: number;
  /** Normalized event type. */
  eventType: string;
  /** Event payload with Pi-specific details removed. */
  payload: Record<string, string | number | boolean>;
}

/** Usage summary returned by the spike adapter. */
export interface SpikeUsage {
  /** Input token count reported by the provider. */
  inputTokens: number;
  /** Output token count reported by the provider. */
  outputTokens: number;
  /** Total token count reported by the provider. */
  totalTokens: number;
}

/** Result of one Pi task execution through Marga. */
export interface SpikeTaskResult {
  /** Final assistant text. */
  text: string;
  /** Provider stop reason. */
  stopReason: string;
  /** Number of partial text updates observed during streaming. */
  streamingDeltaCount: number;
  /** Names of tools actually executed by the Pi loop. */
  executedTools: string[];
  /** Normalized platform events. */
  events: SpikeEvent[];
  /** Token usage from the last assistant message. */
  usage: SpikeUsage;
}

interface TextBlock {
  type: "text";
  text: string;
}

interface AssistantMessageLike {
  role: string;
  stopReason?: string;
  usage?: {
    input?: number;
    output?: number;
    totalTokens?: number;
  };
  content: readonly unknown[];
}

/**
 * Narrow an unknown content block to a Pi text block.
 *
 * @param block - Content block from an assistant message.
 * @returns True when the block carries text.
 */
function isTextBlock(block: unknown): block is TextBlock {
  return (
    typeof block === "object" &&
    block !== null &&
    (block as { type?: unknown }).type === "text" &&
    typeof (block as { text?: unknown }).text === "string"
  );
}

/**
 * Concatenate all text blocks from a transcript.
 *
 * @param messages - Pi transcript messages.
 * @returns Concatenated assistant text.
 */
export function assistantText(messages: readonly unknown[]): string {
  const parts: string[] = [];
  for (const message of messages) {
    if (typeof message !== "object" || message === null) {
      continue;
    }
    const candidate = message as AssistantMessageLike;
    if (candidate.role !== "assistant") {
      continue;
    }
    for (const block of candidate.content) {
      if (isTextBlock(block)) {
        parts.push(block.text);
      }
    }
  }
  return parts.join("");
}

/**
 * Extract the last assistant message from a transcript.
 *
 * @param messages - Pi transcript messages.
 * @returns The last assistant message, or undefined when absent.
 */
function lastAssistant(messages: readonly unknown[]): AssistantMessageLike | undefined {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (
      typeof message === "object" &&
      message !== null &&
      (message as AssistantMessageLike).role === "assistant"
    ) {
      return message as AssistantMessageLike;
    }
  }
  return undefined;
}

/**
 * Count text deltas in a Pi stream event.
 *
 * @param event - Agent lifecycle event.
 * @returns Number of incremental text updates carried by the event.
 */
function textDeltaCount(event: AgentEvent): number {
  if (event.type !== "message_update") {
    return 0;
  }
  const nested = event.assistantMessageEvent as { type?: unknown; delta?: unknown };
  return nested.type === "text_delta" && typeof nested.delta === "string" ? 1 : 0;
}

/**
 * Minimal Pi runtime adapter used by the Milestone 0 compatibility spike.
 *
 * It maps the platform task contract onto the real pinned Pi loop and injects
 * a W3C trace context into every model request sent to Marga.
 */
export class KartaSpikeRuntime {
  /** Validated spike configuration. */
  private readonly config: RuntimeConfig;

  /**
   * Create the runtime adapter.
   *
   * @param config - Validated spike configuration.
   */
  constructor(config: RuntimeConfig) {
    this.config = config;
  }

  /**
   * Build the OpenAI-compatible Pi model pointing at Marga.
   *
   * @param headers - Trace propagation headers injected into model requests.
   * @returns Pi model descriptor.
   */
  private model(headers: Record<string, string>): Model<"openai-completions"> {
    return {
      id: this.config.modelId,
      name: "karta-spike-model",
      api: "openai-completions",
      provider: "marga",
      baseUrl: this.config.margaBaseUrl.replace(/\/+$/, ""),
      reasoning: false,
      input: ["text"],
      contextWindow: 8192,
      maxTokens: 256,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      headers,
    };
  }

  /**
   * Build the deterministic tool used to verify Pi tool calling.
   *
   * @returns Pi agent tool definition.
   */
  private addTool(): AgentTool<object, ToolDetails> {
    return {
      name: "add",
      label: "Add two integers",
      description: "Add two integers and return their sum",
      parameters: {
        type: "object",
        properties: {
          a: { type: "number", description: "First operand" },
          b: { type: "number", description: "Second operand" },
        },
        required: ["a", "b"],
      },
      execute: async (toolCallId: string, rawParams: unknown): Promise<AgentToolResult<ToolDetails>> => {
        const params = asAddParams(rawParams);
        if (params === undefined) {
          return {
            content: [{ type: "text", text: "Invalid arguments: expected numeric a and b" }],
            details: { toolName: "add", sum: 0 },
            isError: true,
          };
        }
        const sum = params.a + params.b;
        return {
          content: [{ type: "text", text: String(sum) }],
          details: { toolName: "add", sum },
          structuredContent: { sum },
          ...(toolCallId.length === 0 ? { isError: true } : {}),
        };
      },
    };
  }

  /**
   * Execute one task through Pi and Marga.
   *
   * @param task - User prompt for the agent.
   * @returns Structured result with streaming, tool and trace evidence.
   */
  async executeTask(task: string): Promise<SpikeTaskResult> {
    return await startTrace("karta.spike.task", async (span) => {
      span.setMetadata({
        "karta.tenant_id": this.config.tenantId,
        "karta.task_id": this.config.taskId,
        "karta.spike": "milestone-0",
      });

      const carrier: Record<string, string> = {};
      propagation.inject(context.active(), carrier);
      const headers: Record<string, string> = {
        ...carrier,
        "x-karta-task-id": this.config.taskId,
      };

      const streamFn: StreamFn = (model, requestContext, options) =>
        streamSimple(model, requestContext, {
          ...options,
          apiKey: this.config.apiKey,
          headers,
        });

      const agent = new Agent({
        initialState: {
          systemPrompt: "Use the add tool for arithmetic and then report the result briefly.",
          model: this.model(headers),
          tools: [this.addTool()],
        },
        streamFn,
        sessionId: this.config.taskId,
      });

      const events: SpikeEvent[] = [];
      const executedTools: string[] = [];
      let streamingDeltaCount = 0;
      const unsubscribe = agent.subscribe((event: AgentEvent) => {
        streamingDeltaCount += textDeltaCount(event);
        if (event.type === "tool_execution_end") {
          executedTools.push(event.toolName);
        }
        events.push({
          sequence: events.length + 1,
          eventType: event.type,
          payload: { tenantId: this.config.tenantId, taskId: this.config.taskId },
        });
      });

      try {
        await agent.prompt(task);
        await agent.waitForIdle();
      } finally {
        unsubscribe();
      }

      const messages = agent.state.messages as readonly unknown[];
      const last = lastAssistant(messages);
      const usage: SpikeUsage = {
        inputTokens: last?.usage?.input ?? 0,
        outputTokens: last?.usage?.output ?? 0,
        totalTokens: last?.usage?.totalTokens ?? 0,
      };
      span.setResult(assistantText(messages).slice(0, 200));
      return {
        text: assistantText(messages),
        stopReason: last?.stopReason ?? "unknown",
        streamingDeltaCount,
        executedTools,
        events,
        usage,
      };
    });
  }
}

/**
 * Pi runtime adapter implementing the documented kartā execution contract.
 *
 * Pi-specific types never leave this module: the control plane receives only
 * the normalized `AgentEvent` and `ExecutionResult` JSON schemas.
 */

import { randomUUID } from "node:crypto";

import {
  Agent,
  type AgentEvent as PiAgentEvent,
  type StreamFn,
} from "@earendil-works/pi-agent-core";
import type { Model } from "@earendil-works/pi-ai";
import { streamSimple } from "@earendil-works/pi-ai/compat";

import type { AgentEvent, ExecutionRequest, ExecutionResult, UsageSummary } from "./contracts.js";
import { workspaceTools, type WorkspaceTool } from "./tools.js";

interface TextBlock {
  type: "text";
  text: string;
}

interface AssistantMessageLike {
  role: string;
  stopReason?: string;
  usage?: { input?: number; output?: number; totalTokens?: number };
  content: readonly unknown[];
}

/**
 * Narrow unknown content blocks to Pi text blocks.
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
 * Concatenate all assistant text blocks in a transcript.
 *
 * @param messages - Pi transcript messages.
 * @returns Final assistant text.
 */
export function assistantText(messages: readonly unknown[]): string {
  const parts: string[] = [];
  for (const message of messages) {
    if (typeof message !== "object" || message === null) {
      continue;
    }
    const candidate = message as AssistantMessageLike;
    if (candidate.role !== "assistant" || !Array.isArray(candidate.content)) {
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
 * @returns Last assistant message, or undefined when absent.
 */
function lastAssistant(messages: readonly unknown[]): AssistantMessageLike | undefined {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (typeof message === "object" && message !== null && (message as AssistantMessageLike).role === "assistant") {
      return message as AssistantMessageLike;
    }
  }
  return undefined;
}

/**
 * Redact credentials and URLs from an error before returning it to callers.
 *
 * @param error - Thrown value.
 * @returns Bounded, sanitized error description.
 */
export function safeErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : "unknown error";
  return raw
    .replace(/Bearer\s+\S+/gi, "Bearer [redacted]")
    .replace(/https?:\/\/\S+/gi, "[url]")
    .slice(0, 300);
}

/**
 * Adapt the pinned Pi Agent loop to the kartā platform contract.
 */
export class KartaRuntimeAdapter {
  /**
   * Build the OpenAI-compatible Pi model descriptor pointing at Marga.
   *
   * @param request - Validated execution request.
   * @param headers - Propagation headers injected into model requests.
   * @returns Pi model descriptor.
   */
  private model(request: ExecutionRequest, headers: Record<string, string>): Model<"openai-completions"> {
    return {
      id: request.model,
      name: "karta-runtime-model",
      api: "openai-completions",
      provider: "marga",
      baseUrl: request.marga_base_url,
      reasoning: false,
      input: ["text"],
      contextWindow: 8192,
      maxTokens: 512,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      headers,
    };
  }

  /**
   * Execute one task through Pi and Marga.
   *
   * @param request - Validated execution contract.
   * @returns Normalized execution result with ordered events and usage.
   */
  async execute(request: ExecutionRequest): Promise<ExecutionResult> {
    const headers: Record<string, string> = {
      "x-karta-task-id": request.task_id,
      "x-correlation-id": request.correlation_id,
    };
    const streamFn: StreamFn = (model, context, options) =>
      streamSimple(model, context, { ...options, apiKey: request.api_key, headers });

    const allowed = new Set(request.profile.tools);
    const tools: WorkspaceTool[] = workspaceTools(request.workspace_path).filter((tool) =>
      allowed.has(tool.name),
    );
    const agent = new Agent({
      initialState: {
        systemPrompt: request.profile.instructions,
        model: this.model(request, headers),
        tools,
      },
      streamFn,
      sessionId: request.session_id,
    });

    const events: AgentEvent[] = [];
    let toolCalls = 0;
    let turns = 0;
    let limitExceeded: string | null = null;

    const emit = (eventType: string, payload: Record<string, unknown>): void => {
      events.push({
        event_id: randomUUID(),
        tenant_id: request.tenant_id,
        task_id: request.task_id,
        session_id: request.session_id,
        sequence: events.length + 1,
        event_type: eventType,
        occurred_at: new Date().toISOString(),
        payload,
        correlation_id: request.correlation_id,
        trace_id: null,
      });
    };

    const unsubscribe = agent.subscribe((event: PiAgentEvent) => {
      if (event.type === "turn_start") {
        turns += 1;
        if (turns > request.limits.max_iterations) {
          limitExceeded = "max_iterations";
          agent.abort();
        }
        return;
      }
      if (event.type === "message_update") {
        const nested = event.assistantMessageEvent;
        if (nested.type === "text_delta") {
          emit("message.delta", { delta: nested.delta });
        }
        return;
      }
      if (event.type === "message_end") {
        if ((event.message as { role?: unknown }).role === "assistant") {
          emit("message.complete", {});
        }
        return;
      }
      if (event.type === "tool_execution_start") {
        emit("tool.started", { tool_name: event.toolName });
        return;
      }
      if (event.type === "tool_execution_end") {
        toolCalls += 1;
        emit("tool.completed", { tool_name: event.toolName, is_error: event.isError });
        if (toolCalls >= request.limits.max_tool_calls) {
          limitExceeded = "max_tool_calls";
          agent.abort();
        }
      }
    });

    try {
      await agent.prompt(request.prompt);
      await agent.waitForIdle();
    } catch (error) {
      return {
        task_id: request.task_id,
        status: "failed",
        final_text: "",
        stop_reason: "error",
        events,
        usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
        error: safeErrorMessage(error),
      };
    } finally {
      unsubscribe();
    }

    const messages = agent.state.messages as readonly unknown[];
    const last = lastAssistant(messages);
    const usage: UsageSummary = {
      input_tokens: last?.usage?.input ?? 0,
      output_tokens: last?.usage?.output ?? 0,
      total_tokens: last?.usage?.totalTokens ?? 0,
    };
    if (limitExceeded !== null) {
      return {
        task_id: request.task_id,
        status: "failed",
        final_text: assistantText(messages),
        stop_reason: "limit",
        events,
        usage,
        error: `Execution limit exceeded: ${limitExceeded}`,
      };
    }
    return {
      task_id: request.task_id,
      status: "completed",
      final_text: assistantText(messages),
      stop_reason: last?.stopReason ?? "unknown",
      events,
      usage,
      error: null,
    };
  }
}

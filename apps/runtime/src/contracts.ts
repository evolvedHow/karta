/**
 * Documented JSON contracts exchanged between the Python control plane and
 * the TypeScript Pi runtime. Field names are snake_case to match the Pydantic
 * schemas in `packages/karta/models.py`.
 */

/** Structured, tenant-scoped task event. */
export interface AgentEvent {
  event_id: string;
  tenant_id: string;
  task_id: string;
  session_id: string;
  sequence: number;
  event_type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
  correlation_id: string | null;
  trace_id: string | null;
}

/** Token usage reported by the provider. */
export interface UsageSummary {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

/** Subset of the agent profile needed by the runtime. */
export interface ProfileDefinition {
  id: string;
  version: string;
  instructions: string;
  tools: string[];
  model_policy: {
    strong: string;
    economical_coding?: string;
  };
  limits: {
    max_iterations: number;
    max_tool_calls: number;
    max_execution_minutes: number;
  };
}

/** Request sent by the control plane to `POST /v1/execute`. */
export interface ExecutionRequest {
  task_id: string;
  tenant_id: string;
  session_id: string;
  prompt: string;
  workspace_path: string;
  profile: ProfileDefinition;
  marga_base_url: string;
  model: string;
  api_key: string;
  correlation_id: string;
  limits: {
    max_iterations: number;
    max_tool_calls: number;
    max_execution_minutes: number;
  };
}

/** Result returned by `POST /v1/execute`. */
export interface ExecutionResult {
  task_id: string;
  status: "completed" | "failed";
  final_text: string;
  stop_reason: string;
  events: AgentEvent[];
  usage: UsageSummary;
  error: string | null;
}

/** Return whether an unknown value is a plain object. */
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Read a required string from a validated object.
 *
 * @param record - Object to read from.
 * @param key - Field name.
 * @returns Non-empty string value.
 * @throws Error when the field is absent or not a non-empty string.
 */
export function requiredString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Field ${key} must be a non-empty string`);
  }
  return value;
}

/**
 * Read a required positive integer from a validated object.
 *
 * @param record - Object to read from.
 * @param key - Field name.
 * @returns Positive integer value.
 * @throws Error when the field is not a positive integer.
 */
export function positiveInt(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new Error(`Field ${key} must be a positive integer`);
  }
  return value;
}

/**
 * Parse a profile definition from untrusted transport data.
 *
 * @param value - Raw profile object.
 * @returns Validated profile definition.
 * @throws Error when required fields are missing or malformed.
 */
export function parseProfile(value: unknown): ProfileDefinition {
  if (!isRecord(value)) {
    throw new Error("profile must be an object");
  }
  const modelPolicy = value["model_policy"];
  const limits = value["limits"];
  if (!isRecord(modelPolicy) || !isRecord(limits)) {
    throw new Error("profile.model_policy and profile.limits must be objects");
  }
  const rawTools = value["tools"];
  const tools = Array.isArray(rawTools)
    ? rawTools.filter((item): item is string => typeof item === "string")
    : [];
  return {
    id: requiredString(value, "id"),
    version: requiredString(value, "version"),
    instructions: typeof value["instructions"] === "string" ? value["instructions"] : "",
    tools,
    model_policy: {
      strong: requiredString(modelPolicy, "strong"),
      ...(typeof modelPolicy["economical_coding"] === "string"
        ? { economical_coding: modelPolicy["economical_coding"] }
        : {}),
    },
    limits: {
      max_iterations: positiveInt(limits, "max_iterations"),
      max_tool_calls: positiveInt(limits, "max_tool_calls"),
      max_execution_minutes: positiveInt(limits, "max_execution_minutes"),
    },
  };
}

/**
 * Validate and normalize an execution request at the HTTP boundary.
 *
 * @param value - Raw JSON body.
 * @returns Validated execution request.
 * @throws Error when the body does not match the contract.
 */
export function parseExecutionRequest(value: unknown): ExecutionRequest {
  if (!isRecord(value)) {
    throw new Error("Execution request must be a JSON object");
  }
  const rawLimits = value["limits"];
  const profile = parseProfile(value["profile"]);
  const effectiveLimits = isRecord(rawLimits)
    ? {
        max_iterations: positiveInt(rawLimits, "max_iterations"),
        max_tool_calls: positiveInt(rawLimits, "max_tool_calls"),
        max_execution_minutes: positiveInt(rawLimits, "max_execution_minutes"),
      }
    : profile.limits;
  return {
    task_id: requiredString(value, "task_id"),
    tenant_id: requiredString(value, "tenant_id"),
    session_id: requiredString(value, "session_id"),
    prompt: requiredString(value, "prompt"),
    workspace_path: requiredString(value, "workspace_path"),
    profile,
    marga_base_url: requiredString(value, "marga_base_url"),
    model: requiredString(value, "model"),
    api_key: typeof value["api_key"] === "string" ? value["api_key"] : "",
    correlation_id: requiredString(value, "correlation_id"),
    limits: effectiveLimits,
  };
}

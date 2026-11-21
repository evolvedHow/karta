/** Environment-driven configuration for the Milestone 0 Pi runtime spike. */
export interface RuntimeConfig {
  /** Base URL of the Marga OpenAI-compatible surface. */
  readonly margaBaseUrl: string;
  /** Model identifier Marga should route. */
  readonly modelId: string;
  /** Placeholder API key accepted by the loopback gateway. */
  readonly apiKey: string;
  /** Tenant identifier stamped on emitted events and spans. */
  readonly tenantId: string;
  /** Task identifier stamped on emitted events and spans. */
  readonly taskId: string;
  /** OTLP/HTTP endpoint receiving OpenLIT spans. */
  readonly otlpEndpoint: string;
  /** Path where the task result JSON is written. */
  readonly resultPath: string;
}

/** Default values used when the corresponding environment variable is unset. */
const DEFAULTS: RuntimeConfig = {
  margaBaseUrl: "http://127.0.0.1:8011/v1",
  modelId: "mock-tool",
  apiKey: "spike-placeholder",
  tenantId: "spike-tenant",
  taskId: "spike-task-0001",
  otlpEndpoint: "http://127.0.0.1:4318",
  resultPath: "artifacts/pi-result.json",
};

/**
 * Read and validate spike configuration from environment variables.
 *
 * @param env - Environment mapping, injectable for unit tests.
 * @returns Validated runtime configuration.
 * @throws Error when a required value is blank.
 */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): RuntimeConfig {
  const values: RuntimeConfig = {
    margaBaseUrl: env.KARTA_SPIKE_MARGA_URL ?? DEFAULTS.margaBaseUrl,
    modelId: env.KARTA_SPIKE_MODEL ?? DEFAULTS.modelId,
    apiKey: env.KARTA_SPIKE_API_KEY ?? DEFAULTS.apiKey,
    tenantId: env.KARTA_SPIKE_TENANT_ID ?? DEFAULTS.tenantId,
    taskId: env.KARTA_SPIKE_TASK_ID ?? DEFAULTS.taskId,
    otlpEndpoint: env.OTEL_EXPORTER_OTLP_ENDPOINT ?? DEFAULTS.otlpEndpoint,
    resultPath: env.KARTA_SPIKE_RESULT_PATH ?? DEFAULTS.resultPath,
  };
  for (const [key, value] of Object.entries(values)) {
    if (value.trim().length === 0) {
      throw new Error(`Configuration value ${key} must not be blank`);
    }
  }
  return values;
}

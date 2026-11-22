/** Environment-driven configuration for the kartā Pi runtime service. */

/** Validated runtime service configuration. */
export interface RuntimeConfig {
  /** Loopback interface to bind. */
  host: string;
  /** HTTP port for the runtime service. */
  port: number;
  /** Shared secret expected in `X-Karta-Internal-Token`. */
  internalToken: string;
  /** Fallback Marga base URL when a request omits one. */
  margaBaseUrl: string;
}

/**
 * Read and validate runtime configuration.
 *
 * @param env - Environment mapping, injectable for tests.
 * @returns Validated configuration.
 * @throws Error when the port or a required value is invalid.
 */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): RuntimeConfig {
  const port = Number(env.KARTA_RUNTIME_PORT ?? "8101");
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("KARTA_RUNTIME_PORT must be a valid TCP port");
  }
  const internalToken = env.KARTA_INTERNAL_TOKEN ?? "";
  if (internalToken.length === 0) {
    throw new Error("KARTA_INTERNAL_TOKEN must be set");
  }
  return {
    host: "127.0.0.1",
    port,
    internalToken,
    margaBaseUrl: (env.KARTA_MARGA_URL ?? "http://127.0.0.1:8010/v1").replace(/\/+$/, ""),
  };
}

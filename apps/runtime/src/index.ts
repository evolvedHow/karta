/** Process entry point for the kartā Pi runtime service. */

import { startRuntimeServer } from "./server.js";

const server = startRuntimeServer();

/**
 * Close the server cleanly on a termination signal.
 *
 * @param signal - Signal that triggered shutdown.
 */
function shutdown(signal: string): void {
  process.stderr.write(`kartā runtime received ${signal}; shutting down\n`);
  server.close(() => process.exit(0));
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

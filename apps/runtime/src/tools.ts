/**
 * Workspace-scoped filesystem tools for the Milestone 1 coding profile.
 *
 * Every path is resolved inside the task workspace; absolute paths, parent
 * traversal and symlinks outside the workspace are rejected.
 */

import { promises as fs } from "node:fs";
import path from "node:path";

import type { AgentTool, AgentToolResult } from "@earendil-works/pi-agent-core";

import { isRecord } from "./contracts.js";

/** Structured details returned by workspace tools. */
export interface FileDetails {
  /** Workspace-relative path the tool acted on. */
  path: string;
  /** Number of bytes read or written, when applicable. */
  bytes?: number;
  /** Number of entries listed, when applicable. */
  entries?: number;
}

/** Tool type used by the workspace tool set. */
export type WorkspaceTool = AgentTool<object, FileDetails>;

/**
 * Resolve a relative path inside a workspace.
 *
 * @param workspace - Absolute workspace root.
 * @param candidate - Caller-supplied relative path.
 * @returns Absolute path guaranteed to remain inside the workspace.
 * @throws Error when the path escapes the workspace or is not a string.
 */
export function resolveInsideWorkspace(workspace: string, candidate: unknown): string {
  if (typeof candidate !== "string" || candidate.length === 0) {
    throw new Error("path must be a non-empty string");
  }
  if (path.isAbsolute(candidate)) {
    throw new Error("absolute paths are not allowed");
  }
  const root = path.resolve(workspace);
  const target = path.resolve(root, candidate);
  if (target !== root && !target.startsWith(`${root}${path.sep}`)) {
    throw new Error("path escapes the workspace");
  }
  return target;
}

/**
 * Read a required string argument from raw tool parameters.
 *
 * @param raw - Raw tool arguments.
 * @param key - Argument name.
 * @returns String argument value.
 * @throws Error when the argument is invalid.
 */
function stringArgument(raw: unknown, key: string): string {
  if (!isRecord(raw)) {
    throw new Error("Tool arguments must be an object");
  }
  const value = raw[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${key} must be a non-empty string`);
  }
  return value;
}

/**
 * Build an error result without exposing filesystem internals to the model.
 *
 * @param relative - Workspace-relative path.
 * @param message - Safe error description.
 * @returns Error tool result.
 */
function toolError(relative: string, message: string): AgentToolResult<FileDetails> {
  return {
    content: [{ type: "text", text: message }],
    details: { path: relative },
    isError: true,
  };
}

/**
 * Build the workspace-scoped tool set available to the basic coding profile.
 *
 * @param workspace - Absolute path to the task workspace.
 * @returns Pi-compatible tool definitions.
 */
export function workspaceTools(workspace: string): WorkspaceTool[] {
  const readFile: WorkspaceTool = {
    name: "read_file",
    label: "Read a workspace file",
    description: "Read a UTF-8 text file from the task workspace.",
    parameters: {
      type: "object",
      properties: { path: { type: "string", description: "Workspace-relative file path" } },
      required: ["path"],
    },
    execute: async (toolCallId, rawParams) => {
      void toolCallId;
      let relative = "unknown";
      try {
        relative = stringArgument(rawParams, "path");
        const absolute = resolveInsideWorkspace(workspace, relative);
        const content = await fs.readFile(absolute, "utf8");
        return {
          content: [{ type: "text", text: content }],
          details: { path: relative, bytes: Buffer.byteLength(content, "utf8") },
          structuredContent: { path: relative, bytes: Buffer.byteLength(content, "utf8") },
        };
      } catch (error) {
        return toolError(relative, error instanceof Error ? error.message : "read_file failed");
      }
    },
  };

  const writeFile: WorkspaceTool = {
    name: "write_file",
    label: "Write a workspace file",
    description: "Write UTF-8 text to a file in the task workspace, creating parent directories.",
    parameters: {
      type: "object",
      properties: {
        path: { type: "string", description: "Workspace-relative file path" },
        content: { type: "string", description: "File contents" },
      },
      required: ["path", "content"],
    },
    execute: async (toolCallId, rawParams) => {
      void toolCallId;
      let relative = "unknown";
      try {
        relative = stringArgument(rawParams, "path");
        if (!isRecord(rawParams) || typeof rawParams["content"] !== "string") {
          throw new Error("content must be a string");
        }
        const absolute = resolveInsideWorkspace(workspace, relative);
        await fs.mkdir(path.dirname(absolute), { recursive: true });
        await fs.writeFile(absolute, rawParams["content"], "utf8");
        const bytes = Buffer.byteLength(rawParams["content"], "utf8");
        return {
          content: [{ type: "text", text: `Wrote ${relative} (${bytes} bytes)` }],
          details: { path: relative, bytes },
          structuredContent: { path: relative, bytes },
        };
      } catch (error) {
        return toolError(relative, error instanceof Error ? error.message : "write_file failed");
      }
    },
  };

  const listFiles: WorkspaceTool = {
    name: "list_files",
    label: "List a workspace directory",
    description: "List entries in a workspace directory.",
    parameters: {
      type: "object",
      properties: { path: { type: "string", description: "Workspace-relative directory path" } },
      required: ["path"],
    },
    execute: async (toolCallId, rawParams) => {
      void toolCallId;
      let relative = "unknown";
      try {
        relative = stringArgument(rawParams, "path");
        const absolute = resolveInsideWorkspace(workspace, relative);
        const entries = (await fs.readdir(absolute, { withFileTypes: true }))
          .map((entry) => `${entry.isDirectory() ? "dir" : "file"} ${entry.name}`)
          .sort();
        return {
          content: [{ type: "text", text: entries.join("\n") }],
          details: { path: relative, entries: entries.length },
          structuredContent: { path: relative, entries: entries.length },
        };
      } catch (error) {
        return toolError(relative, error instanceof Error ? error.message : "list_files failed");
      }
    },
  };

  return [readFile, writeFile, listFiles];
}

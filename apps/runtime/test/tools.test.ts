import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";

import type { AgentToolResult } from "@earendil-works/pi-agent-core";

import type { FileDetails, WorkspaceTool } from "../src/tools.js";
import { resolveInsideWorkspace, workspaceTools } from "../src/tools.js";

/**
 * Return the three workspace tools with an explicit presence check.
 *
 * @param root - Workspace root.
 * @returns Read, write and list tools in that order.
 */
function tools(root: string): [WorkspaceTool, WorkspaceTool, WorkspaceTool] {
  const all = workspaceTools(root);
  const read = all[0];
  const write = all[1];
  const list = all[2];
  if (read === undefined || write === undefined || list === undefined) {
    throw new Error("Workspace tool set is incomplete");
  }
  return [read, write, list];
}

/**
 * Extract text content from a tool result.
 *
 * @param result - Tool result to inspect.
 * @returns First text block or an empty string.
 */
function textOf(result: AgentToolResult<FileDetails>): string {
  const first = result.content[0];
  return first !== undefined && first.type === "text" ? first.text : "";
}

test("resolveInsideWorkspace contains traversal and absolute paths", () => {
  const root = "/tmp/workspace";
  assert.equal(resolveInsideWorkspace(root, "src/main.ts"), path.join(root, "src/main.ts"));
  assert.throws(() => resolveInsideWorkspace(root, "../secret"), /escapes/);
  assert.throws(() => resolveInsideWorkspace(root, "/etc/passwd"), /absolute/);
  assert.throws(() => resolveInsideWorkspace(root, ""), /non-empty/);
});

test("workspace tools round-trip a file and list the directory", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "karta-tools-"));
  const [read, write, list] = tools(root);
  assert.equal(read.name, "read_file");
  assert.equal(write.name, "write_file");
  assert.equal(list.name, "list_files");

  const written = await write.execute("call-1", {
    path: "nested/note.txt",
    content: "hello kartā",
  });
  assert.equal(written.isError, undefined);
  assert.equal((await readFile(path.join(root, "nested/note.txt"), "utf8")), "hello kartā");

  const readResult = await read.execute("call-2", { path: "nested/note.txt" });
  assert.match(textOf(readResult), /hello kartā/);

  const listResult = await list.execute("call-3", { path: "." });
  assert.match(textOf(listResult), /dir nested/);
});

test("workspace tools reject writes outside the workspace", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "karta-tools-"));
  await writeFile(path.join(root, "inside.txt"), "safe", "utf8");
  const [read, write] = tools(root);
  void read;
  const result = await write.execute("call-4", { path: "../outside.txt", content: "bad" });
  assert.equal(result.isError, true);
});

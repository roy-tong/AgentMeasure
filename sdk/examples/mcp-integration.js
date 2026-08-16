#!/usr/bin/env node
/**
 * Integration example: @agentmeasure/mcp middleware on an official MCP SDK server
 * (@modelcontextprotocol/sdk). Tool handlers are wrapped AT REGISTRATION through
 * the official `server.tool` API — arguments/results never touched, nothing on the
 * critical path.
 *
 * Run: node examples/mcp-integration.js
 * Output: ~/.agentmeasure/events/agentmeasure-events.jsonl (canonical observations)
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { agentmeasure } from "../dist/index.js";

const mw = agentmeasure({
  projectId: "github.com/acme/weather-service",
  observerPrincipal: "am-sdk@acme",
  trustDomain: "acme",
  caller: { type: "claimed_agent", runtime: "claude", identityStrength: "declared" },
});

const server = new McpServer({ name: "acme-weather", version: "1.0.0" });

// 注册时包装（官方 API 路径）：任何第三方 MCP server 的 handler 都可被包一层
const origTool = server.tool.bind(server);
const wrappedHandlers = {};
server.tool = (name, schema, handler) => {
  wrappedHandlers[name] = mw.wrapTool(name, handler);
  return origTool(name, schema, wrappedHandlers[name]);
};

// 第三方风格 tool handler：只取入参/产出结果，内容零采集
server.tool("get_weather", { city: z.string() }, async ({ city }) => {
  await new Promise((r) => setTimeout(r, 20 + Math.random() * 300));
  if (Math.random() < 0.12) {
    return { content: [{ type: "text", text: "ERROR: upstream unavailable" }], isError: true };
  }
  return { content: [{ type: "text", text: `weather in ${city}: 22C partly cloudy` }] };
});

// 模拟 3 类外部调用方（claude / codex / unknown UA）各 14 次真实调用
const runtimes = ["claude", "codex", "unknown"];
for (let i = 0; i < 42; i++) {
  const city = ["beijing", "shanghai", "tokyo", "paris"][i % 4];
  mw.am.emit({
    type: "result_consumed",
    surfaceId: "mcp_tool:get_weather",
    payload: { tool_call_id: `ext-${i}` },
  });
  try {
    await wrappedHandlers.get_weather({ city });
  } catch {
    // failure observed by middleware
  }
}
console.log(`42 calls through official MCP SDK registration → ${Object.keys(wrappedHandlers).length} wrapped tool.`);
console.log("Next: python3 product/local-analytics.py ~/.agentmeasure/events/agentmeasure-events.jsonl");
process.exit(0);

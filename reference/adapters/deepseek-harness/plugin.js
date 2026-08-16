/**
 * AgentMeasure — DeepSeek Harness adapter plugin（Cordis）。
 *
 * 订阅 DSH session 事件流，在工具调用边界记录 usage 元数据：
 *   - tool/call    → 执行起点（callId/name）
 *   - tool/result  → 完成 + outcome（经 sourceEventSeqs 配对）
 *
 * 隐私红线（代码级）：arguments / message 内容 / 路径 一律不落盘。
 * 输出：unified usage JSONL（与 collector/normalizer 同构），供本地 collector 消费。
 *
 * 安装：将本文件注册为 profile 的 out-of-tree 插件（dsh plugin --profile <name> add <path>）
 */
import { mkdirSync, appendFileSync } from "node:fs";
import { createHash, randomUUID } from "node:crypto";
import { join, resolve } from "node:path";
import { homedir } from "node:os";
import z from "@deepseek-ai/schemastery";

/** Cordis plugin name. */
const name = "agentmeasure";

/** Required services: 无（session/event 是 ctx 级事件）。 */
const inject = [];

/** Runtime schema. */
const Config = z.object({
	eventsDir: z.string().default(join(homedir(), ".agentmeasure", "events")),
	projectId: z.string().default("github.com/roy-tong/AgentMeasure"),
	doNotTrack: z.boolean().default(false),
	agentHost: z.string().default("deepseek-harness"),
});

function pseudo(raw) {
	return "s-" + createHash("sha256").update(String(raw)).digest("hex").slice(0, 16);
}

function bucket(seconds) {
	if (seconds < 1) return "<1s";
	if (seconds < 10) return "1s-10s";
	if (seconds < 60) return "10s-60s";
	if (seconds < 600) return "1m-10m";
	return ">10m";
}

function apply(ctx, config) {
	if (config.doNotTrack) return;
	const dir = resolve(config.eventsDir);
	mkdirSync(dir, { recursive: true });
	const file = join(dir, "dsh-events.jsonl");
	/** callId -> { name, startedAt }（只存元数据） */
	const pending = new Map();

	ctx.on("session/event", (session, event) => {
		if (event.type === "tool/call") {
			// 执行：只取 name/callId；arguments 一律不落盘。以事件 seq 为键，
			// 因为 tool/result 通过 sourceEventSeqs:[callSeq] 引用
			pending.set(event.seq, {
				name: String(event.name ?? "unknown").slice(0, 120),
				startedAt: Date.now(),
				callId: String(event.callId ?? "").slice(0, 120),
			});
			return;
		}
		if (event.type === "tool/result") {
			const callSeq = event.sourceEventSeqs?.[0];
			const meta = callSeq !== void 0 ? pending.get(callSeq) : null;
			if (!meta) return; // 无配对（证据不足），跳过
			pending.delete(callSeq);
			const outcome = event.message?.isError ? "failure" : "success";
			// 注意：tool/call + tool/result 只证明生命周期完成（completed），
			// 不构成独立佐证——evidence 由 verifier 计算，此处绝不自声明
			const record = {
				event_id: randomUUID(),
				occurred_at: new Date().toISOString(),
				project_id: config.projectId,
				observer_side: "client",
				agent_host: config.agentHost,
				provenance: "platform",
				session_id: pseudo(session?.id ?? "unknown"),
				tool: meta.name,
				lifecycle_stage: "L2", // completed（生命周期阶段，非证据）
				outcome,
				duration_bucket: bucket((Date.now() - meta.startedAt) / 1000),
				trace_id: null,
				tool_use_id: meta.callId,
			};
			appendFileSync(file, JSON.stringify(record) + "\n");
			return;
		}
		// 其它事件（turn/start、user/message、assistant/chunk…）不记录
	});
}

export { Config, apply, inject, name };

/**
 * @agentmeasure/mcp — Provider SDK (Draft 0.4.3, observe-first).
 *
 * Core promises:
 *  - observe first, qualify later: usage_context/validity default "unknown"
 *  - fail-open: never throws into the business handler, never on the critical path
 *  - no content: prompt/input/output/paths are unreachable by design
 *  - canonical output: emits exactly the Canonical Observation Envelope
 *    (schemas/observation.schema.json); caller is declared at most
 *  - durable best-effort buffering with explicit loss accounting
 *    (source_sequence + dropped_since_last_report)
 */
import { randomUUID, createHash } from "node:crypto";
import { mkdirSync, appendFileSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

export const SPEC_VERSION = "agentmeasure-0.4";

export type CallerType = "unknown" | "claimed_agent" | "correlated_agent" | "platform_attested";
export type CallerStrength = "unknown" | "declared" | "correlated" | "attested";
export type ObservationType =
  | "presentation" | "selection" | "attempt_started"
  | "attempt_completed" | "result_consumed" | "task_outcome";

export interface AgentMeasureConfig {
  /** Project identifier (deployment context, not entity authority). */
  projectId?: string;
  /** Observer principal, e.g. "am-sdk@acme". */
  observerPrincipal?: string;
  /** Trust domain of the observer. */
  trustDomain?: string;
  /** Observer side; provider SDK observes at the server boundary. */
  observerSide?: "client" | "server" | "platform";
  /** Events directory (local buffer). Default ~/.agentmeasure/events. */
  eventsDir?: string;
  /** Surface namespace, e.g. "mcp". */
  surfaceNamespace?: string;
  /** Surface id prefix, e.g. "mcp_tool". */
  surfacePrefix?: string;
  /** Caller claim to attach (defaults to unknown; you may set declared from clientInfo). */
  caller?: { type: CallerType; runtime: string; identityStrength: CallerStrength };
  /** Disable all recording. */
  doNotTrack?: boolean;
}

interface EmitOptions {
  type: ObservationType;
  payload: Record<string, unknown>;
  surfaceId?: string;
  durationMs?: number;
  /** Optional explicit operation_id / task_id / retry_of (lineage; only with evidence). */
  operationId?: string;
  taskId?: string;
  retryOf?: string;
}

const BUFFER_LIMIT = 10_000;

export class AgentMeasure {
  private readonly cfg: Required<Pick<AgentMeasureConfig, "projectId" | "observerPrincipal" | "trustDomain" | "observerSide" | "eventsDir" | "surfaceNamespace" | "surfacePrefix" | "doNotTrack">> & AgentMeasureConfig;
  private seq = 0;
  private dropped = 0;
  private readonly file: string;
  private readonly instanceId: string;

  constructor(config: AgentMeasureConfig = {}) {
    const eventsDir = config.eventsDir ?? join(homedir(), ".agentmeasure", "events");
    this.cfg = {
      projectId: config.projectId ?? "local",
      observerPrincipal: config.observerPrincipal ?? "am-sdk@local",
      trustDomain: config.trustDomain ?? "local",
      observerSide: config.observerSide ?? "server",
      eventsDir,
      surfaceNamespace: config.surfaceNamespace ?? "mcp",
      surfacePrefix: config.surfacePrefix ?? "mcp_tool",
      doNotTrack: config.doNotTrack ?? false,
      ...config,
    };
    this.instanceId = `am-${process.pid}-${randomUUID().slice(0, 8)}`;
    this.file = join(eventsDir, "agentmeasure-events.jsonl");
  }

  /** Async, fail-open observation emit. Never throws into the caller. */
  emit(opts: EmitOptions): void {
    if (this.cfg.doNotTrack) return;
    try {
      const envelope = this.build(opts);
      mkdirSync(this.cfg.eventsDir, { recursive: true });
      appendFileSync(this.file, JSON.stringify(envelope) + "\n");
    } catch {
      this.dropped += 1; // explicit loss accounting; never propagate
    }
  }

  private build(opts: EmitOptions): Record<string, unknown> {
    this.seq += 1;
    const payload: Record<string, unknown> = { ...opts.payload };
    if (opts.operationId) payload.operationId = opts.operationId;
    if (opts.taskId) payload.taskId = opts.taskId;
    if (opts.retryOf) payload.retryOf = opts.retryOf;
    if (opts.durationMs !== undefined) payload.duration_ms = Math.round(opts.durationMs);
    const surfaceId = opts.surfaceId ?? `${this.cfg.surfacePrefix}:${String(payload.tool ?? "unknown")}`;
    return {
      spec_version: SPEC_VERSION,
      observation_id: randomUUID(),
      observation_type: opts.type,
      observer: {
        principal: this.cfg.observerPrincipal,
        trust_domain: this.cfg.trustDomain,
        side: this.cfg.observerSide,
      },
      observed_at: new Date().toISOString(),
      deployment_context: { project_id: this.cfg.projectId },
      surface: { surface_id: surfaceId, surface_namespace: this.cfg.surfaceNamespace },
      caller: {
        type: this.cfg.caller?.type ?? "unknown",
        runtime: this.cfg.caller?.runtime ?? "unknown",
        identity_strength: this.cfg.caller?.identityStrength ?? "unknown",
      },
      usage_context: "unknown",   // observe first — qualify later (evidence only)
      validity: "unknown",
      context_source: "none",
      validity_source: "none",
      collection_health: {
        source_instance_id: this.instanceId,
        source_sequence: this.seq,
        sequence_epoch: new Date().toISOString().slice(0, 7),
        dropped_since_last_report: this.dropped,
        buffer_overflow: this.dropped > 0,
      },
      provenance: "wrapper",
      payload,
    };
  }

  /** Buffer depth for health monitoring. */
  get bufferStats(): { path: string; exists: boolean } {
    return { path: this.file, exists: existsSync(this.file) };
  }
}

/** Fingerprint helper (for caller claims / ids); never content. */
export function fingerprint(raw: string): string {
  return "p-" + createHash("sha256").update(String(raw)).digest("hex").slice(0, 20);
}

/**
 * MCP server middleware: wrap a tool handler so every execution emits
 * attempt_started/attempt_completed observations without touching arguments
 * or results.
 *
 *   import { agentmeasure } from "@agentmeasure/mcp";
 *   server.use(agentmeasure({ projectId: "github.com/acme/foo" }));
 */
export function agentmeasure(config: AgentMeasureConfig = {}) {
  const am = new AgentMeasure(config);
  return {
    am,
    wrapTool<A extends unknown[], R>(
      name: string,
      handler: (...args: A) => Promise<R> | R,
    ): (...args: A) => Promise<R> {
      return async (...args: A): Promise<R> => {
        const startedAt = Date.now();
        const callId = randomUUID(); // attempt 级关联键（payload 必须携带 tool_call_id）
        am.emit({ type: "attempt_started", surfaceId: `mcp_tool:${name}`,
                  payload: { tool_call_id: callId } });
        try {
          const result = await handler(...args);
          // isError 是 MCP 元数据字段（非内容）；可安全检查
          const isError =
            typeof result === "object" && result !== null &&
            (result as { isError?: unknown }).isError === true;
          am.emit({
            type: "attempt_completed",
            surfaceId: `mcp_tool:${name}`,
            payload: { tool_call_id: callId, outcome: isError ? "failure" : "success" },
            durationMs: Date.now() - startedAt,
          });
          return result;
        } catch (err) {
          am.emit({
            type: "attempt_completed",
            surfaceId: `mcp_tool:${name}`,
            payload: { tool_call_id: callId, outcome: "failure" },
            durationMs: Date.now() - startedAt,
          });
          throw err; // fail-open: business error propagates normally
        }
      };
    },
  };
}

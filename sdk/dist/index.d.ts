export declare const SPEC_VERSION = "agentmeasure-0.4";
export type UsageContext = "production" | "development" | "test" | "benchmark" | "evaluation" | "synthetic" | "ci" | "demo" | "unknown";
export type Validity = "normal" | "duplicate" | "replay" | "health_check" | "load_test" | "suspected_invalid" | "unknown";
/**
 * Validity values a provider can honestly claim from configuration.
 * `normal` is excluded on purpose: a provider cannot know an attempt is
 * valid — that is derived by the collector (validity_source is
 * provider_configuration, never strong qualification).
 */
export type ProviderValidity = "duplicate" | "health_check" | "load_test" | "suspected_invalid";
export type CallerType = "unknown" | "claimed_agent" | "correlated_agent" | "platform_attested";
export type CallerStrength = "unknown" | "declared" | "correlated" | "attested";
export type ObservationType = "presentation" | "selection" | "attempt_started" | "attempt_completed" | "result_consumed" | "task_outcome";
/** Caller claim. `declared` at most from provider-side observation (TRUST §5). */
export interface CallerClaim {
    type: CallerType;
    runtime: string;
    identityStrength: CallerStrength;
}
/** Per-request context handed to a callerResolver (e.g. MCP request extra). */
export interface CallerContext {
    sessionId?: string;
    request?: unknown;
    /** v1 MCP: client `_meta` passthrough (e.g. echoed sessionId). */
    _meta?: Record<string, unknown>;
    /** Alias accepted for custom integrations. */
    meta?: Record<string, unknown>;
    /** v2 MCP: the request object (ctx.mcpReq) with `_meta`. */
    mcpReq?: {
        _meta?: Record<string, unknown>;
        [key: string]: unknown;
    };
}
export interface AgentMeasureConfig {
    /** Project identifier (deployment context, not entity authority). */
    projectId?: string;
    /** Observer principal, e.g. "am-sdk@acme". */
    observerPrincipal?: string;
    /** Trust domain of the observer. */
    trustDomain?: string;
    /** Observer side; provider SDK observes at the server boundary. */
    observerSide?: "client" | "server" | "platform";
    /** Events directory (local spool). Default $AGENTMEASURE_EVENTS_DIR or ~/.agentmeasure/events. */
    eventsDir?: string;
    /** Surface namespace, e.g. "mcp". */
    surfaceNamespace?: string;
    /** Surface id prefix, e.g. "mcp_tool". */
    surfacePrefix?: string;
    /** Usage context label (default "unknown" — observe first, qualify later). */
    usageContext?: UsageContext;
    /**
     * Validity label the provider can honestly claim (default "unknown").
     * `normal` is NOT settable here — it is derived by the collector.
     */
    validity?: ProviderValidity;
    /** Server-level caller claim — fallback only; per-request resolution wins. */
    caller?: CallerClaim;
    /** Disable all recording. */
    doNotTrack?: boolean;
    /** Max observations held in the memory queue before dropping (default 10_000). */
    bufferLimit?: number;
    /** Background flusher interval in ms (default 200). */
    flushIntervalMs?: number;
    /** Rotate the active spool file past this size in bytes (default 5 MiB). */
    maxSpoolBytes?: number;
    /** Keep at most this many rotated spool files (default 7). */
    maxSpoolFiles?: number;
    /**
     * Active spool file name (default "agentmeasure-events.jsonl").
     * eventsDir MUST NOT be shared between processes in 0.1.x; for multi-process
     * deployments use a per-instance name, e.g.
     * `agentmeasure-events-${process.pid}.jsonl`, and point the collector at the
     * glob `agentmeasure-events-*.jsonl`.
     */
    spoolFileName?: string;
    /** Install SIGTERM/SIGINT handlers that drain the queue before exit (default false). */
    handleSignals?: boolean;
}
interface EmitOptions {
    type: ObservationType;
    payload: Record<string, unknown>;
    surfaceId?: string;
    durationMs?: number;
    usageContext?: UsageContext;
    /** Provider-claimable validity only — "normal" is derived by the collector. */
    validity?: ProviderValidity;
    caller?: CallerClaim;
    /** Lineage (snake_case, per payload schemas). */
    operation_id?: string;
    task_id?: string;
    retry_of?: string;
    /** Deprecated camelCase aliases — still accepted, mapped to snake_case. */
    operationId?: string;
    taskId?: string;
    retryOf?: string;
}
/** Buffer health snapshot (also surfaced in collection_health). */
export interface BufferHealth {
    path: string;
    exists: boolean;
    queueDepth: number;
    spoolBytes: number;
    flushedTotal: number;
    droppedTotal: number;
    droppedSinceLastFlush: number;
    flushFailures: number;
    rotatedFiles: number;
    bufferLimit: number;
    flushing: boolean;
}
export declare class AgentMeasure {
    private readonly projectId;
    private readonly observerPrincipal;
    private readonly trustDomain;
    private readonly observerSide;
    private readonly eventsDir;
    private readonly surfaceNamespace;
    private readonly surfacePrefix;
    private readonly usageContext;
    private readonly validity;
    private readonly caller;
    private readonly doNotTrack;
    private readonly bufferLimit;
    private readonly flushIntervalMs;
    private readonly maxSpoolBytes;
    private readonly maxSpoolFiles;
    private readonly handleSignals;
    private seq;
    private queue;
    private flushing;
    private flushChain;
    private timer;
    private droppedTotal;
    private droppedSinceLastFlush;
    private flushedTotal;
    private flushFailures;
    private rotatedFiles;
    private readonly file;
    private readonly instanceId;
    constructor(config?: AgentMeasureConfig);
    /** Non-blocking observation emit: enqueue only. Never throws. */
    emit(opts: EmitOptions): void;
    /** Flush the memory queue to disk (serialized; resolves when drained). */
    flush(): Promise<void>;
    /** Stop the background flusher and drain pending observations. */
    shutdown(): Promise<void>;
    /** Buffer health for monitoring; also surfaced in collection_health. */
    get bufferHealth(): BufferHealth;
    /** Deprecated alias for bufferHealth (v0.1.0 shape was {path, exists}). */
    get bufferStats(): BufferHealth;
    /**
     * Wrap a tool handler so every execution emits attempt_started /
     * attempt_completed without touching arguments or results.
     *
     *   const wrapped = mw.wrapTool("search", handler, {
     *     getCaller: (ctx) => sessions.get(ctx.sessionId ?? ""),  // per-request
     *   });
     */
    wrapTool<A extends unknown[], R>(name: string, handler: (...args: A) => Promise<R> | R, opts?: {
        caller?: CallerClaim;
        getCaller?: (ctx?: CallerContext) => CallerClaim | undefined;
        /**
         * Deterministic duration override for fixtures/tests: a fixed number or
         * a function sampled at completion-emit time. Production deployments
         * omit this — the middleware then records measured wall time.
         */
        durationMs?: number | (() => number);
    }): (...args: A) => Promise<R>;
    private ensureFlusher;
    private drop;
    private doFlush;
    private maybeRotate;
    private pruneSpool;
    private build;
}
/** Fingerprint helper (for caller claims / ids); never content. */
export declare function fingerprint(raw: string): string;
/**
 * MCP server middleware: wrap tool handlers so every execution emits
 * attempt_started/attempt_completed observations without touching arguments
 * or results.
 *
 *   import { agentmeasure } from "@agentmeasure/mcp";
 *   const mw = agentmeasure({ projectId: "github.com/acme/foo" });
 *   const wrapped = mw.wrapTool(name, handler, { getCaller: resolveCaller });
 */
export declare function agentmeasure(config?: AgentMeasureConfig): {
    am: AgentMeasure;
    wrapTool: <A extends unknown[], R>(name: string, handler: (...args: A) => Promise<R> | R, opts?: {
        caller?: CallerClaim;
        getCaller?: (ctx?: CallerContext) => CallerClaim | undefined;
        /**
         * Deterministic duration override for fixtures/tests: a fixed number or
         * a function sampled at completion-emit time. Production deployments
         * omit this — the middleware then records measured wall time.
         */
        durationMs?: number | (() => number);
    }) => (...args: A) => Promise<R>;
};
export {};

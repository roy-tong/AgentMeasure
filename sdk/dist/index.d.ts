export declare const SPEC_VERSION = "agentmeasure-0.4";
export type CallerType = "unknown" | "claimed_agent" | "correlated_agent" | "platform_attested";
export type CallerStrength = "unknown" | "declared" | "correlated" | "attested";
export type ObservationType = "presentation" | "selection" | "attempt_started" | "attempt_completed" | "result_consumed" | "task_outcome";
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
    caller?: {
        type: CallerType;
        runtime: string;
        identityStrength: CallerStrength;
    };
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
export declare class AgentMeasure {
    private readonly cfg;
    private seq;
    private dropped;
    private readonly file;
    private readonly instanceId;
    constructor(config?: AgentMeasureConfig);
    /** Async, fail-open observation emit. Never throws into the caller. */
    emit(opts: EmitOptions): void;
    private build;
    /** Buffer depth for health monitoring. */
    get bufferStats(): {
        path: string;
        exists: boolean;
    };
}
/** Fingerprint helper (for caller claims / ids); never content. */
export declare function fingerprint(raw: string): string;
/**
 * MCP server middleware: wrap a tool handler so every execution emits
 * attempt_started/attempt_completed observations without touching arguments
 * or results.
 *
 *   import { agentmeasure } from "@agentmeasure/mcp";
 *   server.use(agentmeasure({ projectId: "github.com/acme/foo" }));
 */
export declare function agentmeasure(config?: AgentMeasureConfig): {
    am: AgentMeasure;
    wrapTool<A extends unknown[], R>(name: string, handler: (...args: A) => Promise<R> | R): (...args: A) => Promise<R>;
};
export {};

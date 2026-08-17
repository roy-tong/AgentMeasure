/**
 * @agentmeasure/mcp — Provider SDK (v0.1.1, External-Ready).
 *
 * Core promises:
 *  - observe first, qualify later: usage_context/validity default "unknown";
 *    fixtures may label themselves (e.g. "synthetic") via configuration
 *  - fail-open: emit() never throws into the business handler
 *  - non-blocking: emit() only enqueues into a memory queue; a background
 *    flusher batches writes to disk (never synchronous IO on the request path)
 *  - no content: prompt/input/output/paths are unreachable by design
 *  - canonical output: exactly the Canonical Observation Envelope
 *    (schemas/observation.schema.json); lineage fields are snake_case
 *    (operation_id / task_id / retry_of) per the payload schemas
 *  - caller per-request when a callerResolver is provided; the server-level
 *    caller claim is a fallback for fixtures only
 *  - durable best-effort buffering with explicit loss accounting:
 *    memory queue → batch flush → rotating spool files
 */
import { randomUUID, createHash } from "node:crypto";
import { mkdirSync, renameSync, statSync, unlinkSync } from "node:fs";
import { appendFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { homedir } from "node:os";
export const SPEC_VERSION = "agentmeasure-0.4";
const DEFAULT_BUFFER_LIMIT = 10_000;
const DEFAULT_FLUSH_INTERVAL_MS = 200;
const DEFAULT_MAX_SPOOL_BYTES = 5 * 1024 * 1024;
const DEFAULT_MAX_SPOOL_FILES = 7;
const ACTIVE_FILE = "agentmeasure-events.jsonl";
export class AgentMeasure {
    projectId;
    observerPrincipal;
    trustDomain;
    observerSide;
    eventsDir;
    surfaceNamespace;
    surfacePrefix;
    usageContext;
    validity;
    caller;
    doNotTrack;
    bufferLimit;
    flushIntervalMs;
    maxSpoolBytes;
    maxSpoolFiles;
    seq = 0;
    queue = [];
    flushing = false;
    flushChain = Promise.resolve();
    timer = null;
    droppedTotal = 0;
    droppedSinceLastFlush = 0;
    flushedTotal = 0;
    flushFailures = 0;
    rotatedFiles = 0;
    file;
    instanceId;
    constructor(config = {}) {
        const eventsDir = config.eventsDir ??
            process.env.AGENTMEASURE_EVENTS_DIR ??
            join(homedir(), ".agentmeasure", "events");
        this.projectId = config.projectId ?? "local";
        this.observerPrincipal = config.observerPrincipal ?? "am-sdk@local";
        this.trustDomain = config.trustDomain ?? "local";
        this.observerSide = config.observerSide ?? "server";
        this.eventsDir = eventsDir;
        this.surfaceNamespace = config.surfaceNamespace ?? "mcp";
        this.surfacePrefix = config.surfacePrefix ?? "mcp_tool";
        this.usageContext = config.usageContext ?? "unknown";
        this.validity = config.validity ?? "unknown";
        this.caller = config.caller;
        this.doNotTrack = config.doNotTrack ?? false;
        this.bufferLimit = config.bufferLimit ?? DEFAULT_BUFFER_LIMIT;
        this.flushIntervalMs = config.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS;
        this.maxSpoolBytes = config.maxSpoolBytes ?? DEFAULT_MAX_SPOOL_BYTES;
        this.maxSpoolFiles = config.maxSpoolFiles ?? DEFAULT_MAX_SPOOL_FILES;
        this.instanceId = `am-${process.pid}-${randomUUID().slice(0, 8)}`;
        this.file = join(this.eventsDir, ACTIVE_FILE);
    }
    /** Non-blocking observation emit: enqueue only. Never throws. */
    emit(opts) {
        if (this.doNotTrack)
            return;
        try {
            const envelope = this.build(opts);
            if (this.queue.length >= this.bufferLimit) {
                this.drop();
                return;
            }
            this.queue.push(envelope);
            this.ensureFlusher();
        }
        catch {
            this.drop();
        }
    }
    /** Flush the memory queue to disk (serialized; resolves when drained). */
    flush() {
        this.flushChain = this.flushChain.then(() => this.doFlush());
        return this.flushChain;
    }
    /** Stop the background flusher and drain pending observations. */
    async shutdown() {
        if (this.timer !== null) {
            clearInterval(this.timer);
            this.timer = null;
        }
        await this.flush();
    }
    /** Buffer health for monitoring; also surfaced in collection_health. */
    get bufferHealth() {
        let spoolBytes = 0;
        try {
            spoolBytes = statSync(this.file).size;
        }
        catch {
            /* spool not created yet */
        }
        return {
            path: this.file,
            exists: this.flushedTotal > 0 || this.queue.length > 0,
            queueDepth: this.queue.length,
            spoolBytes,
            flushedTotal: this.flushedTotal,
            droppedTotal: this.droppedTotal,
            droppedSinceLastFlush: this.droppedSinceLastFlush,
            flushFailures: this.flushFailures,
            rotatedFiles: this.rotatedFiles,
            bufferLimit: this.bufferLimit,
            flushing: this.flushing,
        };
    }
    /** Deprecated alias for bufferHealth (v0.1.0 shape was {path, exists}). */
    get bufferStats() {
        return this.bufferHealth;
    }
    /**
     * Wrap a tool handler so every execution emits attempt_started /
     * attempt_completed without touching arguments or results.
     *
     *   const wrapped = mw.wrapTool("search", handler, {
     *     getCaller: (ctx) => sessions.get(ctx.sessionId ?? ""),  // per-request
     *   });
     */
    wrapTool(name, handler, opts) {
        return async (...args) => {
            // MCP handlers receive (args, extra) in v1 and (args, ctx) in v2;
            // the last argument carries the per-request context when present.
            const extra = args.length > 1
                ? args[args.length - 1]
                : undefined;
            const caller = opts?.getCaller?.(extra) ?? opts?.caller ?? this.caller;
            const startedAt = Date.now();
            const callId = randomUUID();
            this.emit({
                type: "attempt_started",
                surfaceId: `mcp_tool:${name}`,
                payload: { tool_call_id: callId },
                caller,
            });
            try {
                const result = await handler(...args);
                // isError is MCP metadata (not content); safe to inspect
                const isError = typeof result === "object" && result !== null &&
                    result.isError === true;
                this.emit({
                    type: "attempt_completed",
                    surfaceId: `mcp_tool:${name}`,
                    payload: { tool_call_id: callId, outcome: isError ? "failure" : "success" },
                    durationMs: Date.now() - startedAt,
                    caller,
                });
                return result;
            }
            catch (err) {
                this.emit({
                    type: "attempt_completed",
                    surfaceId: `mcp_tool:${name}`,
                    payload: { tool_call_id: callId, outcome: "failure" },
                    durationMs: Date.now() - startedAt,
                    caller,
                });
                throw err; // fail-open: business error propagates normally
            }
        };
    }
    // ── internals ──────────────────────────────────────────────────────────
    ensureFlusher() {
        if (this.timer === null) {
            this.timer = setInterval(() => void this.flush(), this.flushIntervalMs);
            if (typeof this.timer.unref === "function")
                this.timer.unref();
        }
    }
    drop() {
        this.droppedTotal += 1;
        this.droppedSinceLastFlush += 1;
    }
    async doFlush() {
        const batch = this.queue.splice(0);
        if (batch.length === 0)
            return;
        this.flushing = true;
        try {
            mkdirSync(this.eventsDir, { recursive: true });
            await this.maybeRotate(batch);
            // stamp the batch with loss accounting as of persistence time, so the
            // on-disk health block reflects what actually happened around it
            const health = {
                dropped_since_last_report: this.droppedSinceLastFlush,
                buffer_overflow: this.droppedSinceLastFlush > 0,
            };
            for (const e of batch) {
                const ch = (e.collection_health ?? {});
                e.collection_health = { ...ch, ...health };
            }
            const lines = batch.map((e) => JSON.stringify(e)).join("\n") + "\n";
            await appendFile(this.file, lines, "utf8");
            this.flushedTotal += batch.length;
            this.droppedSinceLastFlush = 0;
        }
        catch {
            // best-effort: re-enqueue what fits, count the rest as lost
            const room = Math.max(0, this.bufferLimit - this.queue.length);
            const retry = batch.slice(0, room);
            this.queue = [...retry, ...this.queue];
            const lost = batch.length - retry.length;
            if (lost > 0) {
                this.droppedTotal += lost;
                this.droppedSinceLastFlush += lost;
            }
            this.flushFailures += 1;
        }
        finally {
            this.flushing = false;
        }
    }
    async maybeRotate(batch) {
        try {
            const st = statSync(this.file);
            const batchBytes = batch.reduce((n, e) => n + JSON.stringify(e).length + 1, 0);
            if (st.size + batchBytes > this.maxSpoolBytes) {
                const ts = new Date().toISOString().replace(/[:.]/g, "-");
                renameSync(this.file, join(this.eventsDir, `agentmeasure-events-${ts}.jsonl`));
                this.rotatedFiles += 1;
                await this.pruneSpool();
            }
        }
        catch {
            /* no active file yet — nothing to rotate */
        }
    }
    async pruneSpool() {
        let entries;
        try {
            entries = await readdir(this.eventsDir);
        }
        catch {
            return;
        }
        const rotated = entries
            .filter((n) => n.startsWith("agentmeasure-events-") && n.endsWith(".jsonl"))
            .sort();
        const excess = rotated.length - this.maxSpoolFiles;
        for (let i = 0; i < excess; i++) {
            try {
                unlinkSync(join(this.eventsDir, rotated[i]));
            }
            catch {
                /* already gone */
            }
        }
    }
    build(opts) {
        this.seq += 1;
        const payload = { ...opts.payload };
        // lineage: snake_case (canonical); camelCase aliases mapped for compat
        const operationId = opts.operation_id ?? opts.operationId;
        const taskId = opts.task_id ?? opts.taskId;
        const retryOf = opts.retry_of ?? opts.retryOf;
        if (operationId !== undefined)
            payload.operation_id = operationId;
        if (taskId !== undefined)
            payload.task_id = taskId;
        if (retryOf !== undefined)
            payload.retry_of = retryOf;
        if (opts.durationMs !== undefined)
            payload.duration_ms = Math.round(opts.durationMs);
        const surfaceId = opts.surfaceId ?? `${this.surfacePrefix}:${String(payload.tool ?? "unknown")}`;
        const usageContext = opts.usageContext ?? this.usageContext;
        const validity = opts.validity ?? this.validity;
        const caller = opts.caller ?? this.caller;
        return {
            spec_version: SPEC_VERSION,
            observation_id: randomUUID(),
            observation_type: opts.type,
            observer: {
                principal: this.observerPrincipal,
                trust_domain: this.trustDomain,
                side: this.observerSide,
            },
            observed_at: new Date().toISOString(),
            deployment_context: { project_id: this.projectId },
            surface: { surface_id: surfaceId, surface_namespace: this.surfaceNamespace },
            caller: {
                type: caller?.type ?? "unknown",
                runtime: caller?.runtime ?? "unknown",
                identity_strength: caller?.identityStrength ?? "unknown",
            },
            usage_context: usageContext,
            validity,
            context_source: usageContext === "unknown" ? "none" : "provider_configuration",
            // validity_source enum: none | collector_derived | runtime_propagated;
            // the SDK never derives validity itself
            validity_source: "none",
            collection_health: {
                source_instance_id: this.instanceId,
                source_sequence: this.seq,
                sequence_epoch: new Date().toISOString().slice(0, 7),
                dropped_since_last_report: 0, // stamped at flush time with actual loss
                buffer_overflow: false,
            },
            provenance: "wrapper",
            payload,
        };
    }
}
/** Fingerprint helper (for caller claims / ids); never content. */
export function fingerprint(raw) {
    return "p-" + createHash("sha256").update(String(raw)).digest("hex").slice(0, 20);
}
/**
 * MCP server middleware: wrap tool handlers so every execution emits
 * attempt_started/attempt_completed observations without touching arguments
 * or results.
 *
 *   import { agentmeasure } from "@agentmeasure/mcp";
 *   const mw = agentmeasure({ projectId: "github.com/acme/foo" });
 *   const wrapped = mw.wrapTool(name, handler, { getCaller: resolveCaller });
 */
export function agentmeasure(config = {}) {
    const am = new AgentMeasure(config);
    return {
        am,
        wrapTool: am.wrapTool.bind(am),
    };
}

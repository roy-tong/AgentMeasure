# agent-used

**An open measurement standard for agent tool calls: standard + middleware + badge.**

```bash
# Wrap any MCP server; start recording agent calls with one command
agent-used wrap -- npx @your/mcp-server

# Aggregate locally → README badge ("agent calls N/mo")
python3 aggregator.py import --events ~/.agent-used/events/agent-use-events.jsonl
python3 aggregator.py serve --port 8787   # GET /badge/{owner}/{repo}.svg
```

[Whitepaper: The Tool Economy Needs Objective Data](https://roy-tong.github.io/) · [Event standard v1](agent_event_schema.json)

## The problem

In 2026, agents are becoming the most important new distribution channel for software — yet tool authors have no idea how often their tools are called by agents, whether calls succeed, or who is calling. skills.sh counts are self-reported telemetry (gameable, no API); the official MCP registry explicitly provides no adoption data; GitHub exposes no repo-level agent metrics. **The agent economy is being played without a scoreboard.**

## Three-layer measurement standard

| Layer | Question | Implementation |
| --- | --- | --- |
| L1 Identify | Who is calling | MCP `clientInfo` / HTTP `X-Agent-Name` / CLI `AGENT_HOST` |
| L2 Attest | The call is real | Callee-side HMAC-signed receipts (nonce anti-replay) |
| L3 Aggregate | The totals are credible | Open event format + aggregation API + badge + anomaly detection |

**The core difference**: counting happens on the callee side (the wrapper sits at the real call boundary), so callers cannot self-report — unlike every self-reported telemetry system.

## Components

| Component | Status | Description |
| --- | --- | --- |
| `agent_event_schema.json` | ✅ v1 | Open event standard (JSONL, metadata only) |
| `mcp_wrapper.py` | ✅ tested | MCP wrapper: stdio proxy, tools/call interception, clientInfo host ID, L2 signing |
| `aggregator.py` | ✅ tested | Import / verify / stats / badge SVG (stdlib only) |
| CLI wrapper | roadmap | `agent-used run -- <cmd>` |
| HTTP middleware | roadmap | Web service counting |
| Cloud aggregator | roadmap | Cloudflare Workers |

## Privacy & compliance (enforced in code)

- Records only: tool name, outcome, coarse duration, host, time. **Never arguments, content, paths, or identity**
- `DO_NOT_TRACK=1` honored end-to-end; local by default, opt-in aggregation upload
- **Never incentivizes agents to star/follow** (GitHub AUP prohibits automated starring); data comes from the user's own tool events, not GitHub scraping

## Quick start

```bash
# 1. Wrap your MCP server (recording begins)
AGENT_USED_TARGET=github.com/you/your-repo \
  python3 mcp_wrapper.py wrap -- npx @your/mcp-server

# 2. Inspect local events
cat ~/.agent-used/events/agent-use-events.jsonl

# 3. Aggregate locally + badge
python3 aggregator.py import --events ~/.agent-used/events/agent-use-events.jsonl
python3 aggregator.py seed-demo        # optional demo data
python3 aggregator.py serve --port 8787
open http://127.0.0.1:8787/badge/you/your-repo
```

## Roadmap

- M0 ✅ Event standard + MCP wrapper (identification + signing)
- M1 ✅ Local aggregator → ☁️ cloud (Workers)
- M2 CLI wrapper + HTTP middleware + SPEC.md
- M3 3 external adopters + Stage Gate
- Research: native hooks integration with Codex / Claude Code / DeepSeek Harness (agent-platform path)

## License

MIT

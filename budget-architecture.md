# Budget Architecture: Single Origin + Edge Cache

**Author:** Brian Cohn, Principal Solutions Architect
**Date:** March 2026
**Status:** Alternative Proposal
**Scope:** AwesomeStuff.com ML Platform — maximum cost reduction, same QPS peaks

---

## The Uncomfortable Question

The current AWS architecture costs ~$900–1,100/mo to serve 5 ML models with peak QPS of 15–50K. That's ECS Fargate auto-scaling across 2–20 tasks, ElastiCache Redis, ALB, CloudWatch, S3, EC2 training instances.

But look at the actual compute requirements:
- XGBoost inference: **~0.2ms** per prediction
- FAISS ANN lookup: **~1–2ms** per query
- LightGBM inference: **~0.1ms** per prediction
- K-Means assignment: **~0.05ms** per customer

At 15K QPS peak (the highest real-time demand), that's 15,000 × 0.2ms = **3 seconds of CPU per second** — three cores busy. A modern 8-core server running FastAPI + uvicorn handles this at <40% utilization. Add FAISS recommendation lookups and you're still under 60%.

The models are small. The inference is microseconds. The data fits in RAM. We are paying for container orchestration, load balancing, managed caching, and auto-scaling infrastructure to solve a problem that a single server handles with room to spare.

---

## The Architecture

```
Customer Browser
        │
        ▼
  Cloudflare (Reverse Proxy + Edge)
        │
        ├── Workers + KV:  Recs / Prices / Segments  (~1–3ms globally)
        │     cache miss ──┐
        │                  │
        └── Passthrough ───┤
                           ▼
                  Hetzner AX52 (Origin)
                  ┌─────────────────────────────┐
                  │  FastAPI (uvicorn, 8 workers) │
                  │  ├── /predict/fraud           │
                  │  ├── /predict/recommendations  │
                  │  ├── /predict/price            │
                  │  └── /predict/segment          │
                  │                               │
                  │  Models (in-process memory):   │
                  │  ├── XGBoost fraud  (~80MB)    │
                  │  ├── FAISS reco index (~35MB)  │
                  │  ├── LightGBM pricing (~20MB)  │
                  │  └── K-Means segmentation (~5MB)│
                  │                               │
                  │  Redis (localhost):            │
                  │  ├── Velocity features (fraud) │
                  │  ├── Precomputed recs (100K)   │
                  │  ├── Precomputed prices (5K)   │
                  │  └── Segment assignments (1M)  │
                  │                               │
                  │  Training (cron/GitHub Actions):│
                  │  ├── Weekly: XGBoost, ALS+FAISS│
                  │  ├── Daily: LightGBM, K-Means  │
                  │  └── MLflow (local tracking)   │
                  │                               │
                  │  Storage: 2× 1TB NVMe SSD     │
                  │  RAM: 64GB DDR5               │
                  │  CPU: AMD Ryzen 7 7700 (8C/16T)│
                  └─────────────────────────────────┘

Batch outputs ──▶ Cloudflare R2 (reports, CSVs)
Model artifacts ──▶ Cloudflare R2 (versioned backups)
KV sync ──▶ Cloudflare KV (recs, prices, segments)
```

---

## Cost Comparison

### Current: AWS

| Component | Monthly |
|---|---|
| ECS Fargate (all tasks) | $700–1,000 |
| ElastiCache Redis | $301–500 |
| ALB | $42 |
| S3 | $12–24 |
| EC2 Training (spot) | $200–600 |
| CloudWatch | $24–50 |
| **Total** | **$895–$1,117** |

### Proposed: Hetzner + Cloudflare

| Component | Monthly | Notes |
|---|---|---|
| Hetzner AX52 (8C/64GB/2TB) | **$70** | Serves all models + trains + runs Redis |
| Cloudflare Pro plan | **$20** | WAF, DDoS protection, analytics, caching |
| Cloudflare Workers (3 endpoints) | **$5** | $5/mo plan includes 10M requests |
| Cloudflare KV (3 namespaces) | **$5** | Included in Workers paid plan |
| Cloudflare R2 (model artifacts + reports) | **$5** | ~50GB stored, no egress fees |
| Hetzner backup (automated daily) | **$7** | 3 backup slots included at this price |
| **Total** | **$112** | |

### Savings

| | AWS | Hetzner + CF | Savings |
|---|---|---|---|
| Monthly | $1,006 (midpoint) | $112 | **$894/mo (89%)** |
| Annual | $12,072 | $1,344 | **$10,728/yr** |

That's not a typo. The AWS architecture pays a 9x premium for managed services, container orchestration, and auto-scaling that this workload doesn't need.

---

## Why This Works at the Same QPS

### Serving Capacity: Math

The Hetzner AX52 runs an AMD Ryzen 7 7700: 8 cores, 16 threads, 5.3GHz boost.

FastAPI + uvicorn with 8 worker processes, each pinned to a core:

| Model | Inference Time | Peak QPS | CPU Needed | Core Assignment |
|---|---|---|---|---|
| Fraud (XGBoost ONNX) | 0.2ms | 15,000 | 3.0 cores | Workers 1–3 |
| Reco (FAISS fallback) | 1.5ms | 5,000 (after edge cache) | 1.5 cores (peak only) | Workers 4–5 |
| Price (Redis lookup) | 0.1ms | 1,000 (after edge cache) | 0.1 cores | Worker 6 |
| Segment (Redis lookup) | 0.1ms | 500 (after edge cache) | 0.05 cores | Worker 6 |
| **Total at peak** | | | **4.65 cores** | **~58% utilization** |

8 cores available, 4.65 needed at peak (which is Black Friday). Normal operation: ~1.5 cores busy. The server is loafing.

### Memory Budget

| Component | RAM |
|---|---|
| XGBoost model (ONNX) | 80MB |
| FAISS index | 35MB |
| LightGBM models (2) | 25MB |
| K-Means model | 5MB |
| FastAPI + Python (8 workers) | 2GB |
| Redis (velocity + precomputed) | 8GB |
| OS + overhead | 2GB |
| **Total serving** | **~12GB** |
| Training headroom | 52GB available |

64GB RAM, 12GB used for serving. Training gets the remaining 52GB — more than enough for XGBoost/LightGBM on 100K SKUs or 1M customers.

### Network

Hetzner includes 1Gbps unmetered bandwidth. At 15K QPS × 1KB avg response = 15MB/s = 120Mbps. Under 12% of available bandwidth at peak.

---

## Edge Layer: Cloudflare Workers + KV

Identical to the hybrid architecture proposal — three Workers serve precomputed data from KV:

| Endpoint | Data Source | Cache Hit Rate | Edge Latency |
|---|---|---|---|
| Recommendations | KV (nightly batch) | 70–80% | 1–3ms |
| Dynamic Pricing | KV (every 10 min) | 95%+ | 1–3ms |
| Segmentation | KV (daily batch) | 99%+ | 1–3ms |

Cache misses fall through to the Hetzner origin. Cloudflare's reverse proxy adds ~5–10ms for the proxy hop on origin requests (vs. direct), but the edge cache absorbs 70–95% of traffic for these three endpoints. Net latency is dramatically better than AWS-only.

**Fraud detection always hits origin** — same rationale as before (velocity features, audit trail, compliance). Origin latency for fraud: ~30–60ms from US, ~100–150ms from EU. Identical to AWS single-region.

---

## What You Give Up

### 1. Redundancy — Single Point of Failure (Biggest Risk)

One server. If the hardware fails, the motherboard dies, or Hetzner has a datacenter incident, everything goes down.

**Mitigations:**
- Hetzner offers 99.9% SLA on dedicated servers (43 min/mo allowed downtime)
- Automated daily backups to R2 ($7/mo) — full disk images
- Model artifacts and batch outputs already stored in R2 — recoverable on any new server
- **Failover plan:** Spin up a second AX52 (~2 hour provisioning), restore from backup, update Cloudflare DNS (1 minute TTL). Total recovery: ~2.5 hours.
- During outage: Cloudflare edge continues serving cached recs/prices/segments. Only fraud detection is truly down.

**Honest assessment:** If 2.5-hour recovery from a hardware failure is unacceptable, add a second AX52 as hot standby ($70/mo more). Still $182/mo total — 82% cheaper than AWS.

### 2. No Auto-Scaling

ECS Fargate scales from 2→20 tasks automatically. A single server doesn't scale.

**Why this is fine:** The math shows 58% utilization at peak. "Peak" means Black Friday. Normal days are at ~20% utilization. There's no realistic organic growth scenario where 8 cores isn't enough for this workload. If AwesomeStuff grows 5x, that's a good problem — and a $140/mo Hetzner AX102 (16 cores, 128GB) handles it.

**Where it breaks:** A sudden 20x traffic spike (viral event, bot attack) would saturate the server. Cloudflare's DDoS protection absorbs attack traffic. For legitimate viral spikes, the edge cache absorbs recs/prices/segments. Only fraud detection would degrade — and at 20x normal QPS, fraud detection latency increases from 30ms to ~200ms (queuing). Still within the 200ms SLA, barely.

### 3. Training Competes with Serving

On AWS, training runs on separate EC2 instances. On the single-box architecture, training runs on the same machine as serving.

**Why this is manageable:**
- Training is episodic: weekly (fraud, reco) or daily (forecast, segmentation)
- Training duration: 10–30 minutes per model
- Schedule training at 3–4 AM when traffic is lowest
- Linux `nice`/`cgroup` ensures serving processes get CPU priority
- 52GB free RAM during training — more than the EC2 r6i.4xlarge (128GB) since serving only uses 12GB

**Worst case:** If a training run coincides with a traffic spike, inference latency increases by ~2–5ms (CPU contention). Imperceptible to users.

### 4. Compliance and Data Residency

Hetzner datacenters are in Germany and Finland (EU). If AwesomeStuff requires US data residency for PCI/SOC2 compliance, Hetzner doesn't work.

**Alternatives if US residency required:**
- **OVH US** (Vint Hill, Virginia): Similar pricing, US datacenter
- **Vultr Bare Metal** (US regions): $120/mo for comparable specs
- **Latitude.sh** (US): Dedicated servers from $99/mo

The architecture is provider-agnostic — any dedicated server with 8+ cores and 64GB RAM works.

### 5. No Managed Services Safety Net

No CloudWatch auto-alarms. No ECS health checks restarting crashed containers. No AWS support plan.

**What you build instead:**
- `systemd` service with automatic restart on crash (built into Linux)
- Simple health check script (cron every 30s, `curl localhost:8000/health`)
- Cloudflare health checks (free, checks origin every 30s, alerts on failure)
- Uptime monitoring via free tier of UptimeRobot or Cloudflare itself
- Log rotation via `logrotate` (standard Linux)
- Prometheus + Grafana on the same box for metrics (optional, ~200MB RAM)

This is more operational work than managed AWS, but it's standard Linux sysadmin — not rocket science.

---

## Even More Aggressive: Cloudflare-Only Serving

If Cloudflare's Constellation (Workers AI) XGBoost runtime matures, there's a path to eliminate the origin server for serving entirely:

```
Customer Browser
        │
        ▼
  Cloudflare Edge (310+ PoPs)
        ├── Worker: Fraud Detection
        │     └── Constellation XGBoost runtime (native, not ONNX)
        │     └── D1 or Durable Objects for velocity features
        ├── Worker: Recommendations ──▶ KV (precomputed)
        ├── Worker: Pricing ──▶ KV (precomputed)
        └── Worker: Segmentation ──▶ KV (precomputed)

Hetzner (training only, not always-on):
  └── Spot/hourly: Train models, export, upload to R2 + Constellation
```

**Estimated cost:** ~$30–60/mo (Workers + KV + R2 + D1) plus $10–20/mo for on-demand training compute.

**Why this doesn't work yet:**
- Constellation XGBoost runtime is early — limited model size support, no FAISS equivalent
- Velocity features for fraud need real-time state. D1 is eventually consistent. Durable Objects provide consistency but at a single location (negating edge benefit for fraud).
- No production-grade MLflow equivalent on Cloudflare — training pipeline still needs a real server

**When it might work:** 12–18 months, as Constellation matures and Durable Objects get SQL query support. Worth watching.

---

## Migration Path

### Week 1: Provision and Configure
1. Order Hetzner AX52 (~2 hour provisioning)
2. Install: Python 3.11, Redis, uvicorn, nginx (reverse proxy), systemd services
3. Deploy FastAPI app with all 5 models
4. Load test: verify 15K QPS sustained with <50ms p99
5. Set up automated backups to Cloudflare R2

### Week 2: Cloudflare Edge Layer
1. Move DNS to Cloudflare (if not already)
2. Deploy 3 Workers (recs, pricing, segmentation) with KV
3. Batch jobs write to both Redis (origin) and KV (edge)
4. Cloudflare reverse proxy points to Hetzner origin IP
5. Verify edge cache hit rates

### Week 3: Cut Over and Decommission AWS
1. Route production traffic through Cloudflare → Hetzner
2. Monitor for 48 hours alongside AWS (shadow traffic)
3. Decommission: ECS services, ALB, ElastiCache, CloudWatch alarms
4. Keep S3 bucket for 30 days as backup (then migrate remaining data to R2)
5. Cancel or downgrade AWS account

**Total migration: 3 weeks. Total downtime: zero (shadow traffic during cutover).**

---

## Decision Framework: Which Architecture to Choose

| Factor | AWS (~$1,000/mo) | Hybrid AWS+CF (~$750/mo) | Single Box+CF (~$112/mo) |
|---|---|---|---|
| Monthly cost | $1,000 | $750 | $112 |
| Annual cost | $12,000 | $9,000 | $1,344 |
| Redundancy | High (multi-AZ) | High (AWS) + edge | Low (single server) |
| Latency (US) | 15–30ms | 1–3ms (edge) / 15–30ms (origin) | 1–3ms (edge) / 30–60ms (origin) |
| Latency (EU) | 90–140ms | 1–3ms (edge) / 90–140ms (origin) | 1–3ms (edge) / 10–20ms (origin, EU datacenter) |
| Auto-scaling | Yes (2→20 tasks) | Yes (AWS side) | No (but 58% peak util) |
| Operational complexity | Low (managed) | Medium (two platforms) | Medium (Linux admin + CF) |
| Compliance | US datacenter, SOC2 | US datacenter, SOC2 | EU datacenter (check reqs) |
| Team skill required | AWS/DevOps | AWS + Cloudflare | Linux sysadmin + CF |
| Time to recover from failure | Minutes (auto-heal) | Minutes (AWS auto-heal) | ~2.5 hours (manual) |

### When to pick each:

**AWS ($1,000/mo):** Compliance requires US-based managed infrastructure. Team is AWS-native. Redundancy is non-negotiable. Budget isn't a constraint.

**Hybrid AWS+CF ($750/mo):** International traffic justifies edge latency gains. Want to keep AWS safety net. Willing to manage two platforms for the latency benefit.

**Single Box+CF ($112/mo):** Cost is the priority. The workload is well within single-server capacity. Team is comfortable with Linux operations. 2.5-hour recovery time is acceptable (or add a second box for $182/mo total with hot standby).

---

## The Real Punchline

The AwesomeStuff.com ML platform serves 5 models whose combined inference load fits in 12GB of RAM and 5 CPU cores at peak. The models are small, the math is fast, and the precomputation strategy means 70–95% of user-facing requests are simple key-value lookups.

AWS is charging ~$1,000/mo for orchestration, managed services, and scaling headroom that this workload will never use. A $70 server with Cloudflare in front handles the same QPS at the same latency (better, internationally) for 89% less.

The question isn't whether a single server *can* handle this workload. It obviously can. The question is whether the operational overhead of managing that server — updates, backups, failover — is worth saving $10,700/yr. For most teams shipping a 5-model ML platform, it is.

---

## Sources

- [Hetzner AX52 Dedicated Server](https://www.hetzner.com/dedicated-rootserver/ax52/) — €59/mo, 8C/64GB
- [Hetzner AX102 Dedicated Server](https://www.hetzner.com/dedicated-rootserver/ax102/) — €104/mo, 16C/128GB
- [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/) — $5/mo paid plan
- [Cloudflare Constellation / Workers AI](https://developers.cloudflare.com/workers-ai/) — XGBoost runtime support
- [Cloudflare workers-wonnx (ONNX on Workers)](https://github.com/cloudflare/workers-wonnx) — WASM inference
- [Fly.io Pricing](https://fly.io/pricing/) — scale-to-zero alternative
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/) — $0.04/vCPU-hour

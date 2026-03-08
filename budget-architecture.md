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

## 10x Scale: 150K QPS Fraud, 500K QPS Recommendations

Everything above assumed the original QPS targets (15K fraud, 50K reco). What happens when you 10x the traffic?

Two things break immediately:

1. **The single AX52 can't keep up.** 150K QPS × 0.2ms inference = 30 cores. An 8-core server maxes out at ~40K QPS for fraud.
2. **Cloudflare Workers pricing explodes.** At 500K QPS average for recommendations, that's ~1.3 billion requests/month. Workers at $0.30/million = **$389/mo just for Workers** — and that's before KV read costs ($0.50/million = **$648/mo**). The per-request billing model that saved money at 1x costs more than AWS at 10x.

### The Fix: Kill Workers, Use CDN Caching

Cloudflare's core CDN cache is **unlimited requests on all plans, including Free.** No per-request charge. No per-GB charge. It just works — `Cache-Control` headers on origin responses, Cloudflare caches at 310 PoPs automatically.

The architectural shift: stop treating the edge as a key-value store (Workers + KV) and start treating it as an HTTP cache (standard CDN). Precompute everything into cacheable API responses on the origin. Let Cloudflare's CDN do what it was built for.

### 10x Architecture

```
Customer Browser
        │
        ▼
  Cloudflare CDN (Pro plan, $20/mo, UNLIMITED requests)
        │
        ├── CACHE HIT: /api/recs/{user_id}         Cache-Control: max-age=3600
        ├── CACHE HIT: /api/prices/{sku_id}         Cache-Control: max-age=600
        ├── CACHE HIT: /api/segments/{user_id}      Cache-Control: max-age=86400
        │
        └── CACHE MISS or /api/predict/fraud ────▶ Origin
                                                     │
                                    ┌────────────────────────────────────┐
                                    │      Hetzner AX162                 │
                                    │      48 cores / 256 GB / 2×1.9TB  │
                                    │                                    │
                                    │  FastAPI (uvicorn, 40 workers):    │
                                    │  ├── /api/predict/fraud (real-time)│
                                    │  ├── /api/recs/{user_id} (static) │
                                    │  ├── /api/prices/{sku_id} (static)│
                                    │  └── /api/segments/{uid} (static) │
                                    │                                    │
                                    │  In-memory (mmap + pagecache):     │
                                    │  ├── XGBoost fraud ONNX (80MB)    │
                                    │  ├── Precomputed recs (200MB)     │
                                    │  ├── Precomputed prices (500KB)   │
                                    │  └── Segment assignments (50MB)   │
                                    │                                    │
                                    │  Redis: fraud velocity features   │
                                    │  Training: same box, off-peak     │
                                    └────────────────────────────────────┘
```

### Why CDN Caching Replaces Workers at 10x

| | Workers + KV (1x design) | CDN Cache (10x design) |
|---|---|---|
| Reco requests (500K QPS avg) | $389/mo Workers + $648/mo KV reads | **$0** (included in Pro plan) |
| Price requests (50K QPS avg) | $39/mo Workers + $65/mo KV reads | **$0** |
| Segment requests (5K QPS avg) | ~$4/mo | **$0** |
| Total edge cost | **~$1,145/mo** | **$20/mo** (Pro plan) |

At 10x traffic, Workers + KV costs **57x more** than standard CDN caching for the same job.

### The Precomputation Strategy Changes

At 1x, we precomputed recs for the top 100K active users. At 10x, we precompute for **all users** and serve them as cacheable HTTP responses:

```python
# Origin endpoint — serves precomputed data with cache headers
@app.get("/api/recs/{user_id}")
async def get_recommendations(user_id: str):
    # Lookup from in-memory dict (preloaded from batch output)
    recs = precomputed_recs.get(user_id)
    if not recs:
        recs = popular_items_fallback  # Default for unknown users

    return JSONResponse(
        content={"user_id": user_id, "recommendations": recs},
        headers={
            "Cache-Control": "public, max-age=3600, s-maxage=3600",
            "CDN-Cache-Control": "max-age=3600",  # Cloudflare-specific
            "Vary": "Accept-Encoding"
        }
    )
```

Once a user's recommendations are requested, Cloudflare caches the response at that PoP. Subsequent requests from the same region are served from cache at ~1–3ms. The cache auto-expires in 1 hour (recs) or 10 minutes (prices) — matching the batch refresh cadence.

**Cache purge on batch completion:**
```bash
# After nightly reco batch finishes — purge stale cache
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"prefixes": ["api/recs/"]}'
```

### CPU Math at 10x

| Model | 10x Peak QPS | How Served | Origin QPS (after CDN) | CPU per req | Cores Needed |
|---|---|---|---|---|---|
| Fraud | 150,000 | Real-time inference (always hits origin) | 150,000 | 0.2ms | **30** |
| Reco | 500,000 | Precomputed, CDN cached (60–80% hit) | 100,000–200,000 | 0.01ms (memory read) | **1–2** |
| Pricing | 50,000 | Precomputed, CDN cached (80%+ hit) | 10,000 | 0.01ms | **<1** |
| Segmentation | 5,000 | Precomputed, CDN cached (90%+ hit) | 500 | 0.01ms | **<1** |
| **Total** | **705,000** | | **~300,000** | | **~33 cores** |

The AX162 has 48 cores. At 33 cores peak utilization, that's **69% — still has headroom.**

The trick: precomputed recs/prices/segments served from memory (Python dict backed by mmap or just loaded at startup) cost ~0.01ms per request — essentially a hash table lookup followed by JSON serialization. This is 20x cheaper per request than FAISS inference and eliminates the need to scale inference compute.

### Memory Budget at 10x

| Component | RAM |
|---|---|
| XGBoost fraud model (ONNX) | 80MB |
| Precomputed recs (ALL users, 1M × 200B) | 200MB |
| Precomputed prices (5K SKUs) | 500KB |
| Segment assignments (1M users) | 50MB |
| FastAPI + Python (40 workers) | 8GB |
| Redis (fraud velocity features, 10x users) | 20GB |
| OS + overhead | 4GB |
| **Total serving** | **~33GB** |
| Training headroom | **223GB available** |

256GB RAM, 33GB serving. Training gets 223GB. Comfortable.

### Network at 10x

300K origin QPS × 1KB avg response = 300MB/s = 2.4Gbps.

The AX162 comes with 1Gbps included. Need the **10G uplink addon** (available from Hetzner). Traffic over 20TB/mo costs €1/TB. At 2.4Gbps sustained (unrealistic — this is peak), monthly transfer would be ~780TB → €760/mo additional.

**Realistic estimate:** Average origin traffic is ~20% of peak → ~480Mbps → within 1Gbps included bandwidth. The CDN absorbs 60–80% of total requests. During peak hours (8 hrs/day at peak), monthly transfer is ~90TB → **€70/mo** additional for overages.

Updated AX162 cost: **$235 + $70 bandwidth = ~$305/mo.**

### 10x Cost Comparison

| Component | AWS (10x) | Hetzner + CDN (10x) |
|---|---|---|
| Compute (serving) | ECS Fargate: 50–80 tasks, $5,000–8,000/mo | AX162: **$235/mo** |
| Caching | ElastiCache Redis (r6g.2xlarge+): $1,200–1,800/mo | Redis on-box + CDN: **$0** |
| Load balancer | ALB high-traffic: $300–500/mo | Cloudflare (included): **$0** |
| CDN / Edge | CloudFront: $500–1,500/mo | Cloudflare Pro: **$20/mo** |
| Bandwidth overages | AWS egress: $500–2,000/mo | Hetzner 10G addon: **$70/mo** |
| Training | EC2 spot: $400–1,200/mo | Same box, off-peak: **$0** |
| Monitoring | CloudWatch + DataDog: $200–500/mo | Prometheus on-box + CF analytics: **$0** |
| **Total** | **$8,100–$15,500/mo** | **~$325/mo** |

**That's 25–48x cheaper at 10x scale.**

The gap widens at higher QPS because AWS costs scale linearly (more Fargate tasks, bigger Redis, more egress) while the Hetzner box is flat-rate — you pay the same $235/mo whether you serve 1K or 150K QPS.

### Adding Redundancy at 10x

Single point of failure is worse at 10x because more customers are affected by downtime.

**Option: Two AX162s with Cloudflare Load Balancing**

```
Cloudflare CDN + Load Balancing ($5/mo)
        │
        ├── Health check every 30s
        │
        ├──▶ AX162 #1 (primary)   — $235/mo
        └──▶ AX162 #2 (secondary) — $235/mo
```

- Active-active: both serve fraud traffic (75K QPS each — well within capacity)
- Cloudflare auto-routes around failures in <30 seconds
- Both boxes run training (primary trains, secondary syncs artifacts)

**Total with redundancy: ~$510/mo** — still 16–30x cheaper than AWS at 10x.

### What Breaks at 100x (1.5M QPS Fraud)

At 100x, fraud detection alone needs 300 cores (1.5M × 0.2ms). A single AX162 can't handle it. You'd need:

- 7× AX162 boxes: ~$1,645/mo — still cheaper than AWS at 10x
- Or: revisit Cloudflare Constellation for edge XGBoost inference (if memory limits increase)
- Or: shard fraud detection by user_id hash across multiple origins

The architecture scales horizontally by adding flat-rate boxes behind Cloudflare's load balancer. Each box you add is $235/mo for 48 cores. AWS charges that much for ~3 Fargate tasks.

---

## The Real Punchline

ML inference is fast. XGBoost predicts in 0.2ms. FAISS searches in 1.5ms. A hash table lookup returns in 0.01ms. These are microsecond workloads being deployed on millisecond-priced infrastructure.

At 1x QPS, a $70 Hetzner box handles the load at 58% utilization. At 10x QPS, a $235 Hetzner box handles it at 69% utilization. At 10x with full redundancy, two boxes cost $510/mo — still 16–30x cheaper than AWS.

The cost gap isn't linear — it's exponential. AWS costs scale with QPS (more Fargate tasks, bigger Redis clusters, more egress). Dedicated servers are flat-rate. Cloudflare CDN caching is unlimited. The more traffic you have, the more you save.

But the biggest insight isn't about servers. It's about **precomputation**. When 4 out of 5 models produce batch outputs that can be served as cached HTTP responses, the "ML inference platform" becomes a CDN problem with one real-time endpoint (fraud). And CDN problems are solved problems — solved cheaply, at any scale, by companies that have been doing it for 15 years.

---

## Sources

- [Hetzner AX52 Dedicated Server](https://www.hetzner.com/dedicated-rootserver/ax52/) — €59/mo, 8C/64GB
- [Hetzner AX102 Dedicated Server](https://www.hetzner.com/dedicated-rootserver/ax102/) — €104/mo, 16C/128GB
- [Hetzner AX162 Dedicated Server](https://www.hetzner.com/dedicated-rootserver/ax162-r/) — €199/mo, 48C/256GB (EPYC 9454P)
- [Cloudflare Plans & Pricing](https://www.cloudflare.com/plans/) — Pro $20/mo, unlimited CDN requests
- [Cloudflare CDN Cache Features by Plan](https://developers.cloudflare.com/cache/plans/) — cache behavior per tier
- [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/) — $0.30/million requests (caution at high QPS)
- [Cloudflare R2 Pricing](https://developers.cloudflare.com/r2/pricing/) — $0 egress, $0.36/million Class B reads
- [Cloudflare Workers AI / Constellation](https://developers.cloudflare.com/workers-ai/) — XGBoost runtime support
- [Fly.io Pricing](https://fly.io/pricing/) — scale-to-zero alternative
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/) — $0.04/vCPU-hour

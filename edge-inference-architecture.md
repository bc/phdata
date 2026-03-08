# Edge Inference Architecture: Cloudflare Workers + AWS Hybrid

**Author:** Brian Cohn, Principal Solutions Architect
**Date:** March 2026
**Status:** Proposal
**Scope:** AwesomeStuff.com ML Platform — 5-model deployment

---

## Problem Statement

The current architecture runs all ML inference in a single AWS region (us-east-1). For an e-commerce platform serving customers globally, every prediction request travels to Virginia and back. That round-trip adds 40–150ms of network latency depending on geography — latency that directly impacts conversion rates.

Research consistently shows that every 100ms of latency costs ~1% in revenue for e-commerce. For a platform running fraud checks on checkout, serving personalized recommendations on every page load, and displaying dynamic prices across the catalog, the cumulative latency cost is real.

This document proposes a hybrid architecture that pushes inference to the edge via Cloudflare Workers where it's faster and cheaper, while keeping latency-insensitive and state-heavy workloads on AWS where they belong.

---

## Decision Matrix: What Moves to the Edge

| Model | Current Deploy | Edge Candidate? | Verdict | Rationale |
|---|---|---|---|---|
| Fraud Detection | ECS Fargate (real-time) | **No** | Stay on AWS | Requires real-time Redis state (velocity features), audit trail proximity, PCI compliance scope |
| Recommendation Engine | ECS Fargate + Redis precompute | **Partial** | Edge for cache hits, AWS for misses | 70–80% of requests are precomputed lookups — perfect for KV. FAISS fallback stays on AWS |
| Inventory Forecasting | EC2 batch (daily) | **No** | Stay on AWS | Batch job, no serving latency. Needs 64GB RAM, Snowflake access |
| Customer Segmentation | ECS one-shot (daily) | **Yes (serving)** | Edge for segment lookups | Segment assignments are static between daily runs. KV lookup replaces API call |
| Dynamic Pricing | ECS batch (every 10 min) | **Yes (serving)** | Edge for price serving | Prices precomputed every 10 min, stored in KV. ~1–5K SKUs fits easily in KV |

**Summary:** Training and batch scoring stay on AWS. Serving of precomputed results moves to the edge. Real-time inference with state dependencies (fraud) stays on AWS.

---

## Architecture

### Current: Everything on AWS

```
Customer Browser
        │
        ▼
   AWS ALB (us-east-1)
        │
        ├──▶ ECS Fargate: Fraud Detection    ◀── Redis (velocity features)
        ├──▶ ECS Fargate: Recommendations     ◀── Redis (precomputed top-20)
        ├──▶ ECS Fargate: Price API            ◀── Redis (precomputed prices)
        └──▶ ECS Fargate: Segment API          ◀── Redis (segment assignments)

Training: EC2 ──▶ MLflow ──▶ S3 (model artifacts)
Batch:    GitHub Actions ──▶ EC2/ECS ──▶ S3/Redis
```

**Latency profile (New York customer):** ~15–30ms p50, ~50–80ms p99
**Latency profile (London customer):** ~90–140ms p50, ~180–250ms p99
**Latency profile (Tokyo customer):** ~120–180ms p50, ~220–300ms p99

### Proposed: Hybrid Edge + AWS

```
Customer Browser
        │
        ▼
   Cloudflare Edge (310+ PoPs)
        │
        ├──▶ Worker: Recommendations ──▶ KV lookup (precomputed top-20)
        │       └── cache miss? ──▶ AWS ECS (FAISS inference) ──▶ backfill KV
        │
        ├──▶ Worker: Dynamic Pricing ──▶ KV lookup (precomputed prices)
        │       └── price not found? ──▶ AWS ECS (fallback) ──▶ backfill KV
        │
        ├──▶ Worker: Segmentation ──▶ KV lookup (segment assignment)
        │       └── unknown user? ──▶ return default segment
        │
        └──▶ Passthrough to AWS ──▶ Fraud Detection (ECS + Redis)

AWS (us-east-1):
   ├── ECS Fargate: Fraud Detection (real-time, unchanged)
   ├── ECS Fargate: FAISS Reco fallback (cache-miss only)
   ├── Redis: Velocity features (fraud only now)
   ├── Batch jobs: Training, scoring, KV population
   └── S3 + MLflow: Model artifacts, tracking

Cloudflare:
   ├── Workers: Edge inference/serving (3 endpoints)
   ├── KV: Precomputed recommendations, prices, segments
   └── R2: Model artifacts (if needed for ONNX-on-edge later)
```

---

## Model-by-Model Breakdown

### 1. Recommendation Engine — Edge Cache + AWS Fallback

**Current flow:**
```
Request ──▶ ALB ──▶ ECS ──▶ Check Redis for precomputed recs
                              ├── HIT (70-80%): Return cached top-20  (~5ms)
                              └── MISS (20-30%): FAISS inference       (~15-30ms)
```

**Proposed flow:**
```
Request ──▶ CF Worker ──▶ KV.get(`recs:user:{id}`)
                           ├── HIT (70-80%): Return from edge         (~1-3ms)
                           └── MISS (20-30%): fetch() to AWS ECS
                                               ├── FAISS inference    (~15-30ms + network)
                                               └── KV.put() backfill  (async, don't block response)
```

**What changes:**
- Nightly batch job writes precomputed recs to **both** Redis (for fraud features) and Cloudflare KV (for edge serving)
- KV population: GitHub Actions calls Cloudflare KV bulk write API after batch scoring
- 100K users × 20 recs × ~200 bytes/rec = ~400MB in KV (well within KV limits)
- KV keys expire after 36 hours (stale-if-not-refreshed)

**Improvement:**
| Metric | Before | After | Delta |
|---|---|---|---|
| p50 latency (US) | 5ms | 1–3ms | -60% |
| p50 latency (EU) | 90ms | 1–3ms | -97% |
| p50 latency (APAC) | 130ms | 1–3ms | -98% |
| ECS Fargate tasks needed | 2–15 (auto-scale) | 1–4 (cache-miss only) | -70% |
| Monthly ECS cost (reco) | $600–800 | $150–250 | -70% |
| Cloudflare Workers cost | $0 | ~$15–30 | — |

**Drawback:** KV has eventual consistency (~60s propagation globally). A user who just purchased an item might still see it recommended for up to 60 seconds. Acceptable for recommendations — this is not a correctness-critical path.

---

### 2. Dynamic Pricing — Edge Serving from KV

**Current flow:**
```
Request ──▶ ALB ──▶ ECS ──▶ Redis.get(`sku:{id}:price`)  (~8-15ms from US, ~100ms+ from EU)
```

**Proposed flow:**
```
Request ──▶ CF Worker ──▶ KV.get(`price:sku:{id}`)        (~1-3ms globally)
                           └── MISS: return base price from KV fallback key
```

**What changes:**
- Every 10-minute pricing batch writes results to Cloudflare KV (in addition to or instead of Redis)
- ~5K SKUs × ~100 bytes = ~500KB total in KV (trivial)
- KV TTL set to 15 minutes (slightly longer than refresh interval for overlap safety)
- Worker includes business logic for price display formatting, currency conversion

**Improvement:**
| Metric | Before | After | Delta |
|---|---|---|---|
| p50 latency (US) | 8–15ms | 1–3ms | -75% |
| p50 latency (EU) | 90–110ms | 1–3ms | -97% |
| ECS Fargate tasks (pricing serve) | 1 task always-on | 0 | -100% |
| Monthly ECS cost (pricing serve) | ~$50–75 | $0 | -100% |
| Cloudflare Workers cost | $0 | ~$5–10 | — |

**Drawback:** Prices could be stale by up to ~70 seconds (10-min batch interval + 60s KV propagation). For most e-commerce, this is acceptable — the cart/checkout flow should always re-validate price server-side before charging. The edge price is a display price, not a transaction price.

**Important:** The checkout price validation must still hit AWS directly (or a Worker that calls AWS) to ensure the customer is never charged a stale price. The edge serves display prices only.

---

### 3. Customer Segmentation — Edge Lookup

**Current flow:**
```
Marketing API ──▶ ALB ──▶ ECS ──▶ Redis.get(`segment:user:{id}`)  (~10-20ms)
```

**Proposed flow:**
```
Marketing API ──▶ CF Worker ──▶ KV.get(`seg:user:{id}`)           (~1-3ms)
                                 └── MISS: return "general" default segment
```

**What changes:**
- Daily segmentation batch writes assignments to KV
- 1M users × ~50 bytes = ~50MB in KV (well within limits)
- KV TTL: 36 hours
- Unknown users get a default segment rather than an error

**Improvement:**
| Metric | Before | After | Delta |
|---|---|---|---|
| p50 latency | 10–20ms | 1–3ms | -85% |
| ECS task (segment serve) | Shared with other APIs | Eliminated | — |

**Drawback:** Segment assignments are 24 hours stale at maximum. For marketing campaign targeting, this is a non-issue — campaigns are planned on longer horizons than daily.

---

### 4. Fraud Detection — Stays on AWS (No Edge)

**Why not edge:**

1. **Real-time state dependency.** Fraud detection requires velocity features — "how many transactions has this user made in the last 1 hour / 24 hours?" These features live in Redis ElastiCache and are updated in near-real-time. Replicating this state to 310 edge locations is architecturally impractical and would introduce consistency windows that create exploitable gaps.

2. **The 128MB memory limit.** The XGBoost model itself is small (~50–80MB as ONNX), but the velocity feature computation, fraud rule engine, and response payload assembly collectively push against the 128MB Worker isolate limit. One OOM in production on a checkout transaction is unacceptable.

3. **Audit and compliance proximity.** Fraud decisions must be logged with full feature vectors for regulatory audit. These logs must be written to a durable, compliant store (S3 + CloudWatch) within the same security boundary as the transaction processing system. Writing audit logs from 310 edge locations to a central store adds complexity and latency to the critical path.

4. **Latency isn't the bottleneck.** Fraud detection runs on the checkout path, which is already a multi-step server-side flow (payment processor call, inventory reservation, order creation). The ~15–30ms p50 inference time is <10% of total checkout latency. Moving it to the edge would save ~5–10ms while adding significant architectural risk.

**Verdict:** The risk-reward ratio is wrong. Keep fraud on AWS, close to Redis and the transaction system.

---

### 5. Inventory Forecasting — Stays on AWS (No Edge)

**Why not edge:** This is a batch job that runs once daily on an EC2 instance with 64GB RAM, processing 100K SKUs against Snowflake data. There is no serving component to move to the edge. The output is a CSV report and S3 upload — not an API.

**Verdict:** No edge component. Not applicable.

---

## Cloudflare Workers Implementation

### Worker Code Pattern (Recommendations Example)

```javascript
// recommendations-worker.js
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const userId = url.searchParams.get("user_id");

    if (!userId) {
      return new Response(JSON.stringify({ error: "user_id required" }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      });
    }

    // Edge lookup — sub-millisecond
    const cached = await env.RECS_KV.get(`recs:${userId}`, "json");

    if (cached) {
      return new Response(JSON.stringify({
        user_id: userId,
        recommendations: cached,
        source: "edge-cache",
        served_from: request.cf?.colo || "unknown"
      }), {
        headers: {
          "Content-Type": "application/json",
          "X-Served-By": "cloudflare-edge",
          "X-Cache": "HIT"
        }
      });
    }

    // Cache miss — fall back to AWS origin
    const origin = await fetch(
      `${env.AWS_ORIGIN}/api/recommendations?user_id=${userId}`,
      { headers: { "Authorization": `Bearer ${env.ORIGIN_TOKEN}` } }
    );

    const data = await origin.json();

    // Backfill KV asynchronously (don't block response)
    if (origin.ok) {
      env.ctx.waitUntil(
        env.RECS_KV.put(`recs:${userId}`, JSON.stringify(data.recommendations), {
          expirationTtl: 129600 // 36 hours
        })
      );
    }

    return new Response(JSON.stringify({
      ...data,
      source: "origin-fallback",
      served_from: request.cf?.colo || "unknown"
    }), {
      headers: {
        "Content-Type": "application/json",
        "X-Served-By": "aws-origin",
        "X-Cache": "MISS"
      }
    });
  }
};
```

### KV Population (Batch Sync)

After the nightly recommendation batch job completes on AWS:

```python
# kv_sync.py — runs as post-batch step in GitHub Actions
import httpx
import json

CF_ACCOUNT_ID = os.environ["CF_ACCOUNT_ID"]
CF_KV_NAMESPACE = os.environ["CF_KV_NAMESPACE_RECS"]
CF_API_TOKEN = os.environ["CF_API_TOKEN"]

def sync_recs_to_kv(recommendations: dict[str, list]):
    """Bulk-write precomputed recommendations to Cloudflare KV."""
    # KV bulk write API accepts up to 10,000 key-value pairs per call
    pairs = [
        {"key": f"recs:{user_id}", "value": json.dumps(recs), "expiration_ttl": 129600}
        for user_id, recs in recommendations.items()
    ]

    # Chunk into batches of 10,000
    for i in range(0, len(pairs), 10000):
        chunk = pairs[i:i+10000]
        resp = httpx.put(
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
            f"/storage/kv/namespaces/{CF_KV_NAMESPACE}/bulk",
            headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
            json=chunk
        )
        resp.raise_for_status()

# Same pattern for prices (every 10 min) and segments (daily)
```

---

## Cost Comparison

### Current: AWS-Only

| Component | Monthly Cost |
|---|---|
| ECS Fargate — Fraud (2–5 tasks) | $300–350 |
| ECS Fargate — Recommendations (2–15 tasks) | $600–800 |
| ECS Fargate — Batch jobs (Pricing, Segmentation) | $100–150 |
| ElastiCache Redis | $301–500 |
| ALB | $42 |
| S3 | $12–24 |
| EC2 Training (spot) | $200–600 |
| CloudWatch | $24–50 |
| **Total** | **$895–$1,117/mo** |

### Proposed: Hybrid Edge + AWS

| Component | Monthly Cost | Change |
|---|---|---|
| ECS Fargate — Fraud (unchanged) | $300–350 | — |
| ECS Fargate — Recommendations (cache-miss only, 1–4 tasks) | $150–250 | **-$450–550** |
| ECS Fargate — Batch jobs (unchanged) | $100–150 | — |
| ElastiCache Redis (smaller, fraud-only) | $150–250 | **-$150–250** |
| ALB (less traffic) | $30 | -$12 |
| S3 | $12–24 | — |
| EC2 Training (unchanged) | $200–600 | — |
| CloudWatch | $24–50 | — |
| **Cloudflare Workers (3 endpoints)** | **$25–50** | new |
| **Cloudflare KV (3 namespaces)** | **$10–20** | new |
| **Total** | **$635–$865/mo** | **-$230–$280/mo saved** |

### Annual Savings

| Scenario | Annual Savings |
|---|---|
| Conservative (low traffic) | ~$2,760 |
| Expected (moderate traffic) | ~$3,060 |
| High traffic (Black Friday scaling) | ~$4,500+ |

**Note:** The savings are modest in absolute terms because the current AWS architecture is already lean (~$1K/mo). The real value proposition is latency reduction, not cost — though the cost reduction is a nice side effect. At higher scale (10x traffic), the edge architecture saves significantly more because KV lookups don't scale cost linearly the way ECS auto-scaling does.

---

## Latency Improvements

### Before (AWS-only, by geography)

| Region | Reco p50 | Pricing p50 | Segment p50 | Fraud p50 |
|---|---|---|---|---|
| US East | 15–30ms | 8–15ms | 10–20ms | 15–30ms |
| US West | 40–60ms | 30–45ms | 35–50ms | 40–60ms |
| Europe | 90–140ms | 90–110ms | 80–120ms | 90–140ms |
| APAC | 120–180ms | 110–150ms | 100–140ms | 120–180ms |

### After (Hybrid, by geography)

| Region | Reco p50 | Pricing p50 | Segment p50 | Fraud p50 |
|---|---|---|---|---|
| US East | **1–3ms** | **1–3ms** | **1–3ms** | 15–30ms (unchanged) |
| US West | **1–3ms** | **1–3ms** | **1–3ms** | 40–60ms (unchanged) |
| Europe | **1–3ms** | **1–3ms** | **1–3ms** | 90–140ms (unchanged) |
| APAC | **1–3ms** | **1–3ms** | **1–3ms** | 120–180ms (unchanged) |

**Biggest wins:** International customers. A London customer loading a product page currently waits ~90ms for recommendations + ~90ms for price = ~180ms of ML latency. With edge serving, that drops to ~4–6ms total. That's a 30x improvement on the page load path that directly affects conversion.

---

## Specific Drawbacks and Risks

### 1. Eventual Consistency in KV (Real Risk — Manageable)

Cloudflare KV guarantees eventual consistency with ~60-second propagation globally. This means:
- A price updated in the batch run takes up to 70 seconds to appear at all edge locations (10-min batch interval + 60s propagation)
- Recommendations updated nightly could show stale results for up to 60 seconds after batch completion

**Mitigation:** This is acceptable for display-layer serving. The checkout flow must always re-validate prices against the AWS origin (source of truth). Recommendations being 60 seconds stale is invisible to users.

**Where this breaks:** If you ever need strongly consistent reads — e.g., "show the user their updated segment immediately after they make a purchase" — KV is the wrong tool. Use Durable Objects instead (but those are more expensive and complex).

### 2. Two Platforms to Operate (Real Risk — Significant)

The team now manages AWS **and** Cloudflare. This means:
- Two sets of credentials, IAM policies, and access controls
- Two monitoring dashboards (CloudWatch + Cloudflare Analytics)
- Two deployment pipelines (ECS deploys + Wrangler deploys)
- Two incident response playbooks
- Two vendor relationships and billing accounts

**Mitigation:** Keep the Cloudflare surface area minimal. Three simple Workers that do KV lookups with AWS fallback. No business logic on the edge beyond cache routing. The Workers are effectively a smart CDN — treat them as infrastructure, not application code.

**Honest assessment:** If the team is small (3–5 people), this operational overhead may not be worth the latency gains. The architecture is most justified when: (a) international traffic is significant, or (b) the team already uses Cloudflare for DNS/CDN.

### 3. GDPR Deletion Propagation (Real Risk — Solvable)

When a user exercises Article 17 Right to Erasure, their data must be deleted from KV within 72 hours. This adds a step to the deletion cascade:

```
Erasure Request
  ├── Delete from Snowflake
  ├── Delete from Redis
  ├── Delete from S3 (training data snapshots)
  ├── Delete from prediction audit logs
  └── NEW: Delete from Cloudflare KV (3 namespaces)
        ├── KV.delete(`recs:user:{id}`)
        ├── KV.delete(`seg:user:{id}`)
        └── (pricing is SKU-keyed, not user-keyed — no action needed)
```

**Mitigation:** Add a KV deletion step to the existing erasure automation. Cloudflare KV delete API is straightforward. The 72-hour SLA gives ample time. But if this step is missed, you have a compliance gap — so it must be in the automated cascade, not a manual process.

### 4. KV Size Limits (Low Risk — Monitor)

Cloudflare KV supports:
- Maximum value size: 25MB per key
- Maximum keys: unlimited (billed per operation)
- Storage: billed at $0.50/GB-month

Current data sizes are well within limits:
- Recommendations: ~400MB (100K users × 20 recs)
- Prices: ~500KB (5K SKUs)
- Segments: ~50MB (1M users)

**Risk scenario:** If the user base grows to 10M+ users, the recommendation KV namespace grows to ~4GB and the KV write costs during nightly batch sync become material (~$2/night for 10M writes). At that scale, consider sharding by user cohort or only caching recommendations for users active in the last 30 days.

### 5. Cold Start / Cache Miss Thundering Herd (Low Risk — Plan For It)

If KV is empty (after a purge, or for a new deployment), all requests become cache misses hitting the AWS origin simultaneously. This could overwhelm the ECS cluster.

**Mitigation:** Pre-warm KV before cutting over DNS. Use a staggered rollout — route 10% of traffic to Workers first, let KV populate, then increase. The Workers code already handles cache misses gracefully (falls back to AWS and backfills asynchronously).

### 6. No Real-Time ONNX Inference on Edge (Limitation — Future Opportunity)

Cloudflare Workers can run ONNX models via WebAssembly, but the 128MB memory limit constrains this to small models (<50MB). The XGBoost fraud model (~50–80MB ONNX) is borderline, and FAISS indexes (35MB+ plus runtime overhead) won't fit reliably.

**Current verdict:** Don't run model inference on Workers. Use Workers as a smart cache layer only.

**Future opportunity:** If Cloudflare increases the memory limit (they've been trending upward — it was 128KB originally, now 128MB), running lightweight ONNX inference on the edge becomes viable. This would let the recommendation engine handle cache misses at the edge without round-tripping to AWS. Worth revisiting in 6–12 months.

---

## What's Genuinely Better vs. Added Complexity

### Genuinely Better

| Aspect | Why |
|---|---|
| International latency for recs/prices/segments | 30–50x faster for EU/APAC customers. This is a real, measurable improvement that impacts conversion. |
| Cost scaling under load | KV lookups cost $0.50/million reads. ECS auto-scaling from 2→15 tasks costs $400+/mo. Edge handles Black Friday traffic without scaling anxiety. |
| Reduced ECS footprint | Reco serving drops from 2–15 tasks to 1–4. Redis can be downsized since it only serves fraud velocity features. |
| CDN-like availability | Cloudflare's 310 PoPs provide inherent geographic redundancy. If us-east-1 has an outage, cached recs/prices/segments still serve from edge (degraded but available). |

### Just Added Complexity (Not Worth It Unless...)

| Aspect | Why It Might Not Be Worth It |
|---|---|
| Fraud detection on edge | The latency gain (~5–10ms) doesn't justify the state replication complexity and compliance risk. |
| Running ONNX on Workers | Memory limits make this fragile. A smart cache is simpler and more reliable than edge inference for now. |
| Multi-cloud operations | If the team is small and doesn't already use Cloudflare, the operational overhead of a second platform may exceed the latency benefit for a US-centric customer base. |

### The Honest Assessment

**If >30% of traffic is international:** This architecture is a clear win. The latency improvements for EU/APAC customers are dramatic (100ms+ → 1–3ms) and directly impact revenue.

**If traffic is 90%+ US-based:** The latency improvement is real but modest (15ms → 3ms). The cost savings (~$3K/yr) are marginal. The main value becomes resilience (edge serving during AWS outages) and future-proofing.

**If the team is <4 engineers:** The operational overhead of managing Cloudflare + AWS may not be worth it. Consider waiting until the team grows or until Cloudflare is already in the stack for other reasons (DNS, WAF, CDN).

---

## Migration Path

### Phase 0: Prerequisites (1 day)
- Set up Cloudflare account, Workers plan, KV namespaces
- Create API tokens for KV write access from GitHub Actions
- Add Cloudflare credentials to GitHub Actions secrets

### Phase 1: Dynamic Pricing on Edge (1 week)
**Why first:** Smallest data volume (~500KB), simplest Worker (pure KV lookup), lowest risk (prices refresh every 10 min so stale data resolves quickly). Fast proof of concept.

1. Add KV sync step to pricing batch job (GitHub Actions)
2. Deploy pricing Worker with fallback to AWS
3. Route pricing API traffic through Cloudflare (DNS change)
4. Monitor: cache hit rate, latency, KV sync timing
5. Validate: compare edge-served prices vs. AWS prices for consistency

### Phase 2: Customer Segmentation on Edge (3 days)
**Why second:** Simple KV lookup, daily refresh, no fallback complexity. Validates KV bulk write at scale (1M keys).

1. Add KV sync to daily segmentation batch job
2. Deploy segmentation Worker
3. Route segment API through Cloudflare
4. Add KV deletion to GDPR erasure automation

### Phase 3: Recommendations on Edge (1 week)
**Why last:** Most complex — requires cache-miss fallback to AWS FAISS, async KV backfill, and validation that recommendation quality doesn't degrade.

1. Add KV sync to nightly recommendation batch job
2. Deploy recommendation Worker with AWS fallback
3. Route recommendation API through Cloudflare
4. Monitor cache hit rate (target: 70–80% from day 1)
5. Scale down ECS recommendation tasks as cache warms
6. Add KV deletion to GDPR erasure automation

### Phase 4: Optimize AWS (1 week)
After edge serving is stable:
1. Downsize Redis (remove recommendation and pricing data, keep fraud velocity features only)
2. Reduce ECS auto-scaling ceilings for recommendation service
3. Update ALB rules (fraud traffic only)
4. Update monitoring dashboards to include Cloudflare metrics
5. Document hybrid architecture in runbooks

**Total migration timeline:** ~3 weeks, done incrementally with rollback at each phase.

---

## Architecture Decision Records

### ADR-1: Edge Caching Over Edge Inference
**Decision:** Use Cloudflare Workers as a smart cache layer (KV lookups) rather than running ONNX inference on the edge.
**Context:** Workers support ONNX via WASM, but the 128MB memory limit makes this fragile for production ML models. KV lookups are deterministic, sub-millisecond, and don't risk OOM.
**Consequence:** Cache misses still require a round-trip to AWS. Accept this tradeoff — the 70–80% cache hit rate for recommendations means only 20–30% of requests pay the origin latency.

### ADR-2: KV Over Durable Objects
**Decision:** Use KV (eventually consistent) over Durable Objects (strongly consistent) for edge state.
**Context:** KV is cheaper ($0.50/million reads vs. Durable Objects pricing), simpler, and eventual consistency is acceptable for display-layer serving (recommendations, prices, segments). Strong consistency would only matter if we were making transactional decisions at the edge — we're not.
**Consequence:** Accept ~60s propagation delay for KV updates. Checkout price validation must always hit AWS origin.

### ADR-3: Fraud Detection Stays Centralized
**Decision:** Do not move fraud detection to the edge under any circumstances.
**Context:** Fraud detection requires real-time velocity features (Redis), produces audit-critical logs, and operates within PCI compliance scope. The latency improvement from edge deployment (~5–10ms) is negligible relative to total checkout latency (~500ms+). The risk of a consistency gap creating a fraud exploitation window is unacceptable.
**Consequence:** International customers pay full round-trip latency for fraud checks on checkout. This is acceptable — checkout is a low-frequency, high-value interaction where users tolerate higher latency.

---

## Summary

Move three serving endpoints to Cloudflare Workers edge (recommendations, pricing, segmentation). Keep fraud detection and all training/batch workloads on AWS. The result: 30x latency improvement for international customers on the page-load path, ~$3K/yr cost savings, and improved resilience — at the cost of managing a second platform and accepting eventual consistency for display-layer data.

The architecture is deliberately conservative: Workers do KV lookups, not inference. The edge is a cache, not a compute layer. This keeps the blast radius small, the Workers code simple, and the fallback path well-understood.

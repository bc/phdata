# ML Model Deployment Framework

A structured evaluation framework for each of AwesomeStuff.com's 5 ML use cases.

---

## The Framework (7 Dimensions)

For each model, evaluate:

| # | Dimension | Why It Matters |
|---|-----------|----------------|
| 1 | **Model & Algorithm** | Simplest effective approach — no over-engineering |
| 2 | **Model Size & Inference** | Parameters, disk size, p50/p99 latency, CPU vs GPU |
| 3 | **Feature Preprocessing** | How complex is the pipeline to get data into the model? |
| 4 | **Peak Load & Serving** | QPS at Black Friday, scaling strategy |
| 5 | **Response Time → Business Impact** | What latency is tolerable before it costs money? |
| 6 | **GDPR Erasure** | What user data touches the model, and how hard is it to delete within 30 days? |
| 7 | **Simplest Platform** | Train → Deploy → Serve with minimum moving parts |

---

## Applied: 5 Models

### A. Fraud Detection (Real-Time)

| Dimension | Assessment |
|-----------|------------|
| **Algorithm** | XGBoost, 300-500 trees, max depth 6-8. Industry standard for tabular fraud. No deep learning needed. |
| **Model size** | ~15-25 MB on disk. ~50-80 MB in memory. Trivial to serve. |
| **Inference** | CPU only. p50 ~2-4 ms, p99 ~8-12 ms (model only). E2E with feature fetch: p50 ~15-30 ms, p99 ~50-80 ms. |
| **Features** | ~80-120 features. Velocity features (txns in last 1h/24h) are the hard part — requires Redis. Everything else is simple numerics + categoricals. Preprocessing: <1 ms if pre-cached. |
| **Peak QPS** | 5,000-15,000 on Black Friday (8-15x normal). A single c5.2xlarge handles ~2-3K QPS. Need 5-8 instances at peak. |
| **Response time** | **Hard limit: 200 ms e2e** (on checkout critical path). Each 100 ms added = ~1% conversion drop. At $500M revenue, that's ~$2M per 1%. False positive rate matters more than latency — target <0.5% FPR. |
| **GDPR erasure** | **HIGH complexity.** User data in: training logs, feature store (Redis), prediction logs. Must cascade-delete from raw tables + feature snapshots + prediction audit log. Model itself doesn't need retraining (single user is negligible in millions). Fraud investigation hold (Art 17(3)(e)) allows 12-18 month retention for legal claims. |
| **Simplest platform** | Train: Python script on ECS scheduled task, weekly. Serve: FastAPI container on ECS + ALB, autoscaling 2-20 replicas. Feature store: Redis (ElastiCache). Track: MLflow. |

**Key insight:** 80% of the engineering work is the feature store (velocity features in Redis), not the model itself.

---

### B. Recommendation Engine (Real-Time)

| Dimension | Assessment |
|-----------|------------|
| **Algorithm** | Two-stage: (1) ALS matrix factorization for candidate retrieval, (2) Optional XGBoost ranker for re-ranking top 50. Skip deep learning (two-tower) unless you have a dedicated ML team. |
| **Model size** | ALS: User matrix 1M users × 128 factors = ~512 MB (but only look up 1 vector at inference = 512 bytes). Item index (FAISS): ~35 MB. Ranker: ~8 MB. |
| **Inference** | FAISS ANN retrieval: p50 ~5-10 ms, p99 ~20-30 ms. With ranking: add 2-4 ms. E2E: p50 ~10-15 ms, p99 ~30-50 ms. CPU is fine at this scale. |
| **Features** | Training: implicit feedback matrix (views, carts, purchases) — sparse matrix, low preprocessing. Inference: single user vector lookup + ANN search. Cold start: fall back to category popularity. **Preprocessing complexity: LOW at inference, MEDIUM at training.** |
| **Peak QPS** | 20,000-50,000 on Black Friday (fires on every page load). BUT: precompute top-20 recs for active users nightly → ~70-80% cache hit rate → real-time QPS drops to 5-15K. |
| **Response time** | **Target: <100 ms.** Often loaded async, so 200-300 ms is tolerable without conversion impact. Quality matters more than speed — 10% relevance improvement = 2-5% GMV uplift. |
| **GDPR erasure** | **MEDIUM-HIGH.** Must delete: interaction logs, user embedding vector (Redis key delete), cached recs, impression/A/B test logs. Model: delete user's row from the ALS user matrix; full retraining on next weekly cycle naturally excludes them. Cross-system propagation to recommendation cache is the real work. |
| **Simplest platform** | Train: PySpark or `implicit` library on r5.4xlarge, weekly. Serve: FastAPI + FAISS in-process + Redis for user vectors. ECS + ALB. Precompute nightly recs for top users into Redis. |

**Key insight:** Precomputing recs for known users and caching aggressively is the #1 scaling lever. The "ML" part is simple — the caching/serving architecture is the real work.

---

### C. Inventory / Demand Forecasting (Batch)

| Dimension | Assessment |
|-----------|------------|
| **Algorithm** | LightGBM global model (one model for all SKUs). 2,000-5,000 trees, ~200 features. Regression target: units sold in next 7/14/28 days. Beats Prophet on accuracy for e-commerce. Fallback for new SKUs: category-level moving average. |
| **Model size** | 60-80 MB on disk. 120-300 MB in memory. Tiny by any standard. |
| **Inference** | Batch only. Score 100K SKUs in ~30-120 seconds on a single CPU. Full pipeline (feature gen + scoring + write): 30-90 min. |
| **Features** | ~150-250 features per (SKU, date). Lag features (sales 7d/14d/28d/1yr ago), rolling stats (7d/28d/90d mean/std/min/max), calendar features, promo flags, category, price tier. **Preprocessing complexity: MEDIUM-HIGH** — lag/rolling features require careful time-based windowing to avoid data leakage. Feature engineering is 60% of the work. |
| **Peak QPS** | N/A — batch. Daily job: 100K SKUs. Weekly deep run: 500K+ SKUs. A single m5.4xlarge handles this easily. |
| **Response time** | **Batch SLA: results by 6 AM daily** (before buying team starts). Missing the forecast → suboptimal replenishment → stockouts. 1% stockout rate on $500M GMV = ~$5M lost sales. |
| **GDPR erasure** | **LOW.** SKU-level model, not user-level. Training data is aggregate sales counts per SKU per day — no individual user data. Deleting a user's orders from raw data could change aggregates, but negligibly at scale. No model retraining needed. |
| **Simplest platform** | Train: Python script triggered by Airflow DAG (or cron + ECS task for <3 jobs). Feature gen in SQL where possible. Write results to Snowflake. Track: MLflow. |

**Key insight:** This is the easiest model to deploy — batch, no user PII, no latency requirements. Feature engineering is the hard part, not serving.

---

### D. Customer Segmentation (Batch)

| Dimension | Assessment |
|-----------|------------|
| **Algorithm** | K-Means on standardized RFM + behavioral features, K=8-15 clusters. PCA (50→15 components) before clustering handles correlation/scale. GMMs give soft assignments if needed. Skip DBSCAN — arbitrary shapes don't map to marketing personas. |
| **Model size** | **<1 MB.** Centroids: 10 clusters × 50 features × 4 bytes = 2 KB. PCA matrix: 3 KB. Scaler: 400 bytes. The model is trivially small — it's just centroid coordinates. |
| **Inference** | Batch. Assign 1M customers in <60 seconds (distance calculation). Full pipeline: 1-4 hours (warehouse query time dominates). |
| **Features** | ~30-80 features. RFM core (recency, frequency, monetary), category preferences (% spend in 10-20 cats), device type, channel responsiveness, return rate. Must StandardScale all features (K-Means is distance-based). Log-transform monetary features. **Preprocessing complexity: LOW-MEDIUM.** |
| **Peak QPS** | N/A — batch weekly/monthly. Output (user→segment) may be queried real-time as a simple Redis key-value lookup (~1 ms). |
| **Response time** | **Batch SLA: before next campaign send (T+24h is fine).** Marketing is not latency-sensitive. Missing a weekly re-segmentation by a day has minimal impact. |
| **GDPR erasure** | **MEDIUM.** Must delete: user's behavioral features, cluster assignment (user_id→segment_id). Model itself: centroids are group statistics — single user deletion doesn't change them. **Cross-system propagation is the real challenge** — segment assignments flow to CRM (Salesforce), email (Braze), ad platforms. All must receive the deletion signal. |
| **Simplest platform** | Train: Honestly, a promoted Jupyter notebook → Python script on cron/ECS task, weekly. Could stay in a notebook for months. Write assignments to Snowflake → Hightouch/Census to sync to CRM. |

**Key insight:** The ML is trivial (K-Means is undergraduate-level). The value is in (1) choosing the right features and (2) operationalizing the segments into downstream marketing systems.

---

### E. Dynamic Pricing (Near-Real-Time)

| Dimension | Assessment |
|-----------|------------|
| **Algorithm** | **Hybrid: ML demand elasticity (batch) + rule engine (real-time).** Offline: LightGBM regression trained on historical price-demand data → outputs price elasticity per SKU. Online: Rule engine applies elasticity + constraints (price floor, ceiling, MAP, competitor parity). Optional: Thompson Sampling bandit for price point A/B testing. Do NOT start with pure RL — business constraints make it impractical. |
| **Model size** | Elasticity LightGBM: 20-50 MB. Per-SKU coefficient table: ~8 MB in Redis (100K SKUs × 10 coefficients). Rule engine: stateless code, no model. |
| **Inference** | Rule engine: p50 <1 ms, p99 <5 ms (just arithmetic). Redis lookup: 1-3 ms. E2E: p50 ~3-8 ms, p99 ~15-25 ms. Precompute elasticity daily in batch; real-time layer is just the rule engine. |
| **Features** | ~80-120 for elasticity model. Demand velocity (rolling sales in 1h/6h/24h — same Redis pattern as fraud), inventory level, competitor price (requires scraping pipeline), promo flags, seasonality. **Preprocessing complexity: MEDIUM.** Same Redis velocity pattern as fraud — if you build it for fraud, reuse it here. |
| **Peak QPS** | 15,000-40,000 on Black Friday (fires on page load for price display). BUT: only 200-500 SKUs may have active dynamic pricing. Price *changes* are lower volume: ~1-5K SKUs/hour. |
| **Response time** | **Target: <50 ms** (price must render with the page — can't be async like recs). Hard limit: 200 ms before cart abandonment risk. **Correctness matters more than speed** — "price shock" (different price shown vs checkout) increases abandonment by 15-25%. |
| **GDPR erasure** | **LOW-MEDIUM.** Elasticity model is SKU-level, not user-level — no user data in the model. Must delete: user session/event logs (if demand velocity uses per-user signals), pricing impression logs (user_id saw price $X). No model retraining needed. |
| **Simplest platform** | Train: Batch LightGBM on Airflow, monthly retrain + daily coefficient refresh → write to Redis. Serve: Rule engine as a FastAPI container on ECS. Same infrastructure as fraud serving. |

**Key insight:** Dynamic pricing is 80% business logic, 20% ML. The rule engine (price floors, competitor parity, margin constraints) is where the real complexity lives. The ML just provides the demand sensitivity signal.

---

## Cross-Cutting Summary

| Model | Size | p99 Latency | Peak QPS | GDPR Risk | Platform Complexity |
|-------|------|-------------|----------|-----------|-------------------|
| Fraud | 25 MB | 50-80 ms e2e | 5-15K | HIGH | MEDIUM (Redis is hard part) |
| Reco | 35 MB serving | 30-50 ms e2e | 20-50K | MED-HIGH | MEDIUM (caching strategy) |
| Forecast | 80 MB | Batch | Batch | LOW | LOW |
| Segmentation | <1 MB | Batch | Batch | MEDIUM | LOW (ML trivial, CRM sync hard) |
| Pricing | 50 MB | 15-25 ms e2e | 15-40K | LOW-MED | MEDIUM (business rules) |

## Shared Infrastructure (build once, use everywhere)

| Component | Used By | Notes |
|-----------|---------|-------|
| **Redis (ElastiCache)** | Fraud, Reco, Pricing | Velocity features, user embeddings, elasticity coefficients, rec cache. Single cluster serves all three. |
| **FastAPI on ECS** | Fraud, Reco, Pricing | Same container pattern for all real-time models. One image per model, ALB routing. |
| **MLflow** | All 5 | Experiment tracking + model registry. S3 artifact store. Set up once. |
| **Snowflake** | All 5 | Training data source + batch output destination. Already in place. |
| **Airflow / ECS cron** | Forecast, Segmentation, Pricing (batch) | Batch orchestration. Airflow if >3 jobs; ECS cron if ≤3. |
| **GDPR deletion pipeline** | All 5 | Event-driven: deletion request → fan out to Redis, Snowflake, S3, prediction logs, downstream systems (CRM, etc.). Build as a Step Function or Airflow DAG. |

## GDPR Deletion Architecture

```
Deletion Request (user_id)
    │
    ├── Redis: DEL user:{id}:* (features, embeddings, cached recs, coefficients)
    ├── Snowflake: DELETE FROM ... WHERE user_id = ? (training data, feature tables)
    ├── S3: Mark for deletion in data catalog (training snapshots)
    ├── Prediction logs: DELETE WHERE user_id = ? (audit/monitoring tables)
    ├── Downstream: Push deletion to CRM, email, ad platforms via reverse ETL
    │
    └── Model retraining: NOT required per-request
        (next scheduled retrain naturally excludes deleted data)

SLA: All deletions complete within 72 hours of request
GDPR deadline: 30 calendar days
Buffer: 27 days for edge cases, manual review, legal holds
```

## Deployment Order (Risk-Adjusted)

| Order | Model | Rationale |
|-------|-------|-----------|
| 1 | **Segmentation** | Lowest risk, batch, <1 MB model, no latency. Quick win for marketing. Validates Snowflake→CRM pipeline. |
| 2 | **Forecasting** | Batch, no user PII, no latency. Validates Airflow + LightGBM pattern. |
| 3 | **Fraud** | First real-time model. Highest business value. Deploy in shadow mode first (score but don't block). Validates Redis + FastAPI + ECS pattern. |
| 4 | **Pricing** | Reuses fraud's Redis + FastAPI infrastructure. Rule engine needs business stakeholder alignment (takes time). |
| 5 | **Reco** | Highest QPS, most complex caching. Deploy last so infrastructure is battle-tested. |

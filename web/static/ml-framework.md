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

#### Velocity Features in Redis — The Core Engineering Challenge

The fraud model is only as good as the features it sees at inference time. The hardest features to compute are **velocity features** — sliding-window aggregations over recent user/device/card activity that must be available in <10 ms. These are the features that separate a toy model from a production fraud system.

**Redis data model:** Each entity (user, device, card) gets a set of sorted sets (ZSET) and counters in Redis, keyed by entity ID. Events are written on every transaction; features are read at scoring time.

```
# Key schema
user:{user_id}:txn_timestamps       → ZSET (score=timestamp, member=txn_id)
user:{user_id}:txn_amounts           → ZSET (score=timestamp, member=amount)
device:{device_hash}:txn_timestamps  → ZSET (score=timestamp, member=txn_id)
card:{card_bin}:txn_timestamps       → ZSET (score=timestamp, member=txn_id)
user:{user_id}:failed_auths          → ZSET (score=timestamp, member=attempt_id)
```

**Example velocity features computed from Redis at scoring time:**

| Feature | Redis Command | Window | Why It Matters |
|---------|--------------|--------|----------------|
| `txn_count_1h` | `ZCOUNT user:{id}:txn_timestamps (now-3600) +inf` | 1 hour | Rapid-fire transactions = stolen card being drained |
| `txn_count_24h` | `ZCOUNT ...` | 24 hours | Unusual daily activity spike |
| `txn_amount_sum_1h` | Sum of `ZRANGEBYSCORE` amounts | 1 hour | Dollar velocity — large spend in short window |
| `txn_amount_avg_7d` | Computed from ZSET | 7 days | Baseline spending pattern for anomaly detection |
| `txn_amount_max_24h` | Max of recent amounts | 24 hours | Single unusually large transaction |
| `distinct_shipping_addr_7d` | `SCARD` of address hashes | 7 days | Multiple shipping addresses = reshipping fraud |
| `distinct_devices_24h` | `SCARD` of device hashes | 24 hours | Account accessed from many devices |
| `failed_auth_count_1h` | `ZCOUNT` on failed auth ZSET | 1 hour | Brute-force account takeover attempts |
| `device_txn_count_1h` | `ZCOUNT device:{hash}:txn_timestamps` | 1 hour | Same device hitting multiple accounts |
| `card_bin_txn_count_24h` | `ZCOUNT card:{bin}:txn_timestamps` | 24 hours | Card BIN being tested across accounts |
| `time_since_last_txn` | `ZREVRANGE ... LIMIT 0 1` → compute delta | N/A | Abnormally fast repeat purchase |
| `is_new_device` | `EXISTS device:{hash}:first_seen` | N/A | Never-before-seen device for this user |
| `account_age_hours` | `GET user:{id}:created_at` → compute delta | N/A | Brand new account + high-value order |
| `avg_txn_interval_7d` | Computed from timestamp diffs | 7 days | Regular cadence vs burst pattern |

**TTL strategy:** ZSETs are trimmed with `ZREMRANGEBYSCORE` to keep only 30 days of history. This bounds Redis memory per user to ~5-10 KB. For 1M active users: ~5-10 GB total — fits in a single ElastiCache r6g.xlarge node.

**Write path:** Every transaction event writes to Kinesis → Lambda consumer → Redis ZADD. Latency: ~50-100 ms from transaction to feature availability.

**Read path:** At scoring time, a single Redis pipeline (MULTI/EXEC) fetches all 14+ features in one round trip. Latency: 1-3 ms.

#### Brian's Notes — Fraud Detection

- **Cart abandonment as a latency canary.** Monitor cart abandonment rate against fraud scoring response time (and all other checkout elements) in real-time. If the fraud check adds enough latency to measurably increase abandonment, we need to know immediately. Build a dashboard that correlates checkout step latency → abandonment rate → revenue impact so we can make data-driven decisions about the tradeoff.

- **A/B testing with a kill switch.** Deploy inference behind a feature flag with A/B testing from day one. Route X% of traffic through the model, remainder through existing rules. If the model degrades or latency spikes, turn it off instantly without a deployment. This also gives us the clean causal measurement of the model's business impact.

- **False positive cost vs. fraud cost — optimize for NOI.** There is a direct, computable relationship between the classification threshold, false positive rate, and lost revenue. Every false positive (legitimate transaction blocked) is a lost sale + customer friction. Every false negative (fraud let through) is a chargeback + fees. Compute the **Net Operating Income (NOI) curve** as a function of the decision threshold: `NOI(t) = Revenue_saved_from_fraud(t) - Revenue_lost_from_false_positives(t) - Chargeback_fees(t)`. The optimal threshold is NOT at the model's accuracy peak — it's at the NOI peak. Run a post-deployment tuning pass to find this optimal operating point on production data.

- **Continuous threshold recalibration.** The optimal decision boundary shifts as fraud patterns evolve and as the business's cost structure changes (e.g., chargeback fees increase, average order value changes seasonally). Schedule quarterly re-evaluation of the threshold using recent production scoring data + actual fraud outcomes.

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

#### Brian's Notes — Recommendation Engine

- **Cart evaluator via association rule mining.** Beyond individual product recommendations, build a separate **cart-level recommender** that uses association rule mining (Apriori / FP-Growth) to identify what item combinations are probable basket completions. If a customer has bread and eggs in their cart, surface milk. This is a fundamentally different signal from collaborative filtering — it's about *this session's intent*, not *this user's history*. Run the association rules as a batch job on historical cart data; serve the top-K rules from a lookup table at cart-view time. Low latency, high business impact.

- **Descriptive clustering for sub-populations.** Before deploying the reco engine, run a descriptive analysis clustering customers by their purchase diversity vs. concentration. Some customers are **narrow specialists** (only buy from 2-3 categories) and some are **broad explorers**. For narrow-interest customers, the recommendation engine should lean heavily toward their known preferences. For broad explorers, diversity in recommendations matters more. This segmentation informs the re-ranking strategy.

- **Per-product vectorization from descriptions and images.** Use pre-trained embeddings (e.g., CLIP for images, sentence-transformers for product descriptions) to create a **product embedding space** independent of user behavior. Then map which product embedding clusters land with which customer clusters. This gives you a content-based recommendation fallback that works for cold-start items AND reveals non-obvious affinities (e.g., customers who buy premium cookware also tend to buy specialty coffee — the visual/description embeddings might capture the "premium lifestyle" cluster).

- **Re-ranking for variety.** The raw model output will often return 10 variations of the same product type (10 brands of batteries). Add a **diversity-aware re-ranker** as a post-processing step: group candidates by category/brand, pick the top candidate from each group, then fill remaining slots by score. The re-ranker should select the specific variant the user is most likely to choose (based on brand affinity, price sensitivity, past purchases) from each group. This is a simple rule-based layer on top of the model — not a separate ML model.

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

#### Brian's Notes — Inventory / Demand Forecasting

- **Per-SKU shipping statistics to time demand response.** The forecast tells you *what* demand will be — but knowing *when to act* requires per-SKU shipping/fulfillment lead times. Enrich the forecasting pipeline with **per-SKU logistics metadata**: average shipping time from supplier, warehouse processing time, last-mile delivery time. Compute for each SKU the "action deadline" — the last date you can place a replenishment order and still have stock before the forecasted demand spike. If the demand spike is 7 days out but the SKU's lead time is 10 days, it's already too late. Surface this as a **"days until action deadline"** metric in the forecast output so the buying team knows which SKUs need immediate action vs. which they have buffer on.

- **Separate "too late" alerting.** Flag SKUs where the forecasted demand spike is inside the lead time window — these are SKUs where the only options are (a) expedited shipping at higher cost, (b) cross-warehouse transfer, or (c) accepting the stockout. This changes the decision from "should we order?" to "what's the cost of expediting vs. the cost of the stockout?" — a different optimization problem that the buying team needs to see clearly.

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

#### Brian's Notes — Customer Segmentation

- **T-SNE / PCA visualization for exploratory analysis.** Before committing to K clusters, run PCA for dimensionality reduction (50→15 components) and T-SNE for 2D visualization. Look for natural groupings by **economic class** (spend tiers), **product category affinity** (electronics buyers vs. grocery buyers vs. fashion buyers), and **engagement pattern** (one-time buyers vs. regulars vs. power users). Use the visual clusters to validate that K-Means is finding meaningful structure, not just carving up noise.

- **LLM-generated cluster titles.** Once clusters are computed, pass each cluster's centroid feature values and a sample of 50-100 representative customers to an LLM (Claude or GPT-4) to generate human-readable segment names and descriptions. Example prompt: "Here are the average feature values for this customer cluster: avg_spend=$420, avg_frequency=2.1/month, top_categories=[Electronics 45%, Home 30%], avg_account_age=3.2 years. Name this segment and describe the persona in 2 sentences." This eliminates the manual naming bottleneck and produces consistent, data-grounded labels.

- **Centroid checkpointing for longitudinal tracking.** Save each clustering run's centroids + labels as a versioned checkpoint (MLflow artifact). When you recluster next month with new data or new customers, you can **map new clusters back to old clusters** by nearest-centroid matching. This lets you track how segments evolve over time (is the "Budget Shoppers" segment growing or shrinking?) and maintain stable segment IDs for downstream systems even as the model is retrained.

- **Enrichment with behavioral and referral data.** Layer on non-purchase signals: which marketing campaigns brought them in, referral source, time-of-day shopping patterns, browsing-to-purchase ratio, return rate. These enrichments can split what looks like one segment into meaningfully different sub-segments (e.g., "high-spend customers acquired via Instagram" behave differently from "high-spend customers acquired via Google Shopping").

- **Retargeting channel clustering.** If we have their Instagram, Facebook, or Pixel data, cluster *within each retargeting channel* separately. The same customer may respond differently to ads on different platforms. Build per-channel segment profiles so the marketing team knows how to approach each segment on each platform — different creative, different frequency caps, different offer types. This turns the segmentation model from a one-dimensional output (segment_id) into a matrix (segment × channel → strategy).

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

#### Brian's Notes — Dynamic Pricing

- **Competitor-weighted demand signals.** Price elasticity should be computed as a function of both **internal demand** (our sales velocity, inventory levels) and **competitive demand** (competitor pricing, competitor availability). Weight competitor signals by how much business each competitor captures in each product category. If Competitor A takes 40% of the market in electronics and Competitor B takes 5%, a price change from A should drive a much larger response than the same change from B. Build a competitor influence matrix: `competitor_weight[competitor][category] = estimated_market_share`. Feed this into the elasticity model as weighted competitive price features.

- **Competitive intelligence pipeline.** This requires a price scraping/monitoring pipeline (or a vendor like Prisync, Competera, or Intelligence Node). Scrape competitor prices daily at minimum, hourly for high-competition SKUs. Store historical competitor prices in Snowflake for training the elasticity model. The scraping pipeline is a non-trivial data engineering effort — budget for it.

- **Dynamic pricing as a margin optimizer, not a race to the bottom.** The goal isn't to always match the lowest price — it's to find the price point that maximizes margin × volume. For SKUs where we have a differentiation advantage (exclusive products, better shipping, loyalty benefits), the model should learn that our elasticity is lower (customers are less price-sensitive) and price accordingly. The rule engine should enforce minimum margin floors to prevent the model from destroying profitability.

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

---

## Sources & Evidence

### A. Fraud Detection — Sources

| Claim | Source | Key Data Point | Year | Confidence |
|-------|--------|---------------|------|------------|
| XGBoost is industry standard for tabular fraud (300-500 trees, depth 6-8) | [ACM — XGBoost Fraud Detection E-commerce](https://dl.acm.org/doi/10.1145/3768801.3768881) + [ML Contests 2024](https://mlcontests.com/state-of-machine-learning-competitions-2024/) | Production e-commerce fraud used n_estimators=300, max_depth=6; GBDTs win majority of tabular competitions | 2024-2025 | High |
| Model ~15-25 MB disk, ~50-80 MB in memory | [Medium — Shrinking XGBoost Model Size](https://medium.com/@gmkrajkumar/shrinking-the-giant-how-i-reduced-my-xgboost-model-size-without-sacrificing-performance-412641a27274) | Compact models (200-300 trees, ~50 features) serialize to 15-50 MB | 2024 | Medium |
| CPU inference p50 ~2-4 ms, p99 ~8-12 ms | [Research Square — CatBoost/XGBoost/LightGBM Comparative](https://www.researchsquare.com/article/rs-7539803/v1) | P99 < 10 ms cited as high-frequency trading threshold; LightGBM 25-30% lower tail latency than XGBoost | 2024-2025 | Medium |
| E2E with feature fetch: p50 ~15-30 ms, p99 ~50-80 ms | [Redis — AI Fraud Detection](https://redis.io/blog/ai-fraud-detection-real-time-intelligence/) | Fraud scoring under 50ms with Redis caching; 20-100+ features within 100ms budget | 2024 | Medium |
| Peak QPS 5K-15K on Black Friday (8-15x normal) | [Stripe BFCM 2024](https://stripe.com/newsroom/news/bfcm2024) + [PayU 2024](https://corporate.payu.com/blog/how-payment-providers-drove-e-commerce-success-during-black-friday/) | Stripe: 137K txn/min peak; PayU: 3,678 req/sec; MONEI: 205% spike vs normal | 2024 | Medium |
| Each 100 ms latency = ~1% conversion drop | [GigaSpaces (Amazon study)](https://www.gigaspaces.com/blog/amazon-found-every-100ms-of-latency-cost-them-1-in-sales/) | Walmart confirmed same finding; widely accepted industry rule | 2006 origin, cited 2024 | High |
| False positive rate target < 0.5% | [GJETA — Real-time Fraud Cloud-Native Fintech](https://gjeta.com/sites/default/files/GJETA-2025-0087.pdf) | Conventional systems avg 3.2% FPR; advanced AI achieves ~0.7%; 0.5% is aspirational | 2025 | Low-Medium |
| GDPR Art 17(3)(e) fraud retention exception | [GDPR-Info.eu — Art. 17](https://gdpr-info.eu/art-17-gdpr/) + [EDPB Guidelines 2024](https://www.edpb.europa.eu/system/files/2024-10/edpb_guidelines_202401_legitimateinterest_en.pdf) | Statutory: "establishment, exercise or defence of legal claims" | Statutory | Very High |
| Velocity features in Redis sliding windows | [Redis Fraud Detection Tutorial](https://redis.io/tutorials/howtos/solutions/fraud-detection/transaction-risk-scoring/) + [Apps in the Open](https://appsintheopen.com/posts/22-calculating-velocity-scores-at-the-speed-of-redis) | 12K-16K velocity scores/sec; ~72K Redis ops/sec per CPU | 2024 | Very High |
| Redis ElastiCache 5-10 GB for 1M users | [Redis FAQ](https://redis.io/docs/latest/develop/get-started/faq/) | 1M simple hashes = ~160 MB; 5-10 GB requires full multi-window ZSET feature store | 2024 | Medium (needs context) |

### B. Recommendation Engine — Sources

| Claim | Source | Key Data Point | Year | Confidence |
|-------|--------|---------------|------|------------|
| ALS effective for e-commerce CF | [arXiv 2410.17644](https://arxiv.org/abs/2410.17644) + [Shaped.ai blog](https://www.shaped.ai/blog/matrix-factorization-the-bedrock-of-collaborative-filtering-recommendations) | 6 MF models evaluated across 4 CF datasets; ALS "highly parallelizable" for implicit feedback | 2024 | High |
| FAISS ANN retrieval: p50 ~5-10 ms, p99 ~20-30 ms | [datasciencebyexample.com](https://www.datasciencebyexample.com/2024/07/07/measure-average-latency-with-faiss-vector-store/) | ~7 ms average latency on 500K vectors (CPU, M1) | 2024 | Partial |
| Precomputed recs: ~70-80% cache hit rate | [Kwai/Kuaishou arXiv](https://arxiv.org/html/2404.14961) + [Redis caching blog](https://redis.io/blog/why-your-cache-hit-ratio-strategy-needs-an-update/) | Kwai reports 40% at peak; Redis targets 80%+; range is system-dependent | 2024 | Partial |
| 10% relevance improvement = 2-5% GMV uplift | [McKinsey personalization](https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights/the-value-of-getting-personalization-right-or-wrong-is-multiplying) | Personalization drives 10-15% revenue lift (5-25% range) | 2021, cited 2024 | Moderate |
| Peak QPS 20K-50K on Black Friday | [Allegro.com Two-Tower paper (ACM RecSys 2025)](https://arxiv.org/html/2508.03702v1) | "20k RPS, 40ms p99 CPU latency" at Allegro production | 2025 | High |
| Apriori/FP-Growth for cart cross-sell | [ACM ICCIT 2024](https://dl.acm.org/doi/full/10.1145/3678610.3678618) | FP-Growth on retail transaction data; 72.1% confidence rules | 2024 | High |
| CLIP + sentence-transformers for product embeddings | [Mercari SigLIP (arXiv)](https://arxiv.org/html/2510.13359v1) + [Walmart VL-CLIP (arXiv 2025)](https://arxiv.org/html/2507.17080) | Mercari: +50% CTR, +14% CVR; Walmart: +18.6% CTR, +4% GMV | 2024-2025 | High |
| Two-tower vs ALS trade-offs | [Allegro.com (ACM RecSys 2025)](https://arxiv.org/html/2508.03702v1) + [Google Cloud docs](https://docs.cloud.google.com/architecture/implement-two-tower-retrieval-large-scale-candidate-generation) | Two-tower: +2.1-2.4% CTR; handles cold-start; ALS faster to train/deploy | 2024-2025 | High |
| Diversity re-ranking improves quality | [ACM TORS 2024](https://dl.acm.org/doi/10.1145/3700604) + [WWW 2024](https://dl.acm.org/doi/10.1145/3589334.3645625) | LLM re-rankers improve ILD with managed relevance trade-off | 2024 | High |

### C. Inventory / Demand Forecasting — Sources

| Claim | Source | Key Data Point | Year | Confidence |
|-------|--------|---------------|------|------------|
| LightGBM global model beats Prophet for e-commerce | [arXiv — Local vs Global Models](https://arxiv.org/html/2411.06394v1) + [M5 Competition](https://phdinds-aim.github.io/time_series_handbook/08_WinningestMethods/lightgbm_m5_forecasting.html) | Global LightGBM outperformed local by 21.42%; used by all top-50 M5 competitors | 2024 + M5 canonical | Moderate-High |
| Model size 60-80 MB / 120-300 MB RAM | Engineering estimate | Plausible for 2K-5K trees, 150-250 features; no published benchmark | — | Weak |
| 100K SKUs in 30-120 sec on single CPU | [Microsoft LightGBM Benchmark](https://microsoft.github.io/lightgbm-benchmark/results/inferencing/) | 394-645 μs per prediction → 100K rows = ~39-65 sec (single thread) | 2023-2024 | Moderate |
| 150-250 features per (SKU, date) | [Netguru — ML for Demand Forecasting](https://www.netguru.com/blog/ml-for-demand-forecasting) | Production pipelines "generate 200-300 derived features" | 2024 | Moderate |
| 1% stockout on $500M GMV = ~$5M lost sales | [Hydrian](https://hydrian.com/library/stockout-cost/) + [HBR Oct 2024](https://hbr.org/2024/10/how-online-retailers-can-avoid-costly-out-of-stock-issues) | Formula: Sales × Stockout Rate × Spill Rate; IHL: stockouts cost $1.2T globally | 2024 | Strong |
| Feature engineering = 60% of the work | [Nature Scientific Reports — Primacy of Feature Engineering](https://www.nature.com/articles/s41598-026-35197-y) | Feature engineering is "primary driver" of accuracy; specific 60% figure is practitioner estimate | 2026 | Weak (concept strong, % not sourced) |
| 2K-5K trees for retail demand | [M5 LightGBM Tuning](https://phdinds-aim.github.io/time_series_handbook/08_WinningestMethods/lightgbm_m5_tuning.html) + [Microsoft Benchmark](https://microsoft.github.io/lightgbm-benchmark/results/inferencing/) | M5 winner: n_estimators=2000, max_depth=4; 5K-tree benchmarked | 2021 (canonical) | Strong |
| Per-SKU shipping lead times for demand timing | [ScienceDirect — Data-driven Lead Time Forecasting](https://www.sciencedirect.com/science/article/abs/pii/S0925527326000769) + [Deposco](https://deposco.com/blog/demand-planning/) | ML-based per-SKU lead time forecasting; "each SKU needs a different lead time" | 2024-2026 | Strong |

### D. Customer Segmentation — Sources

| Claim | Source | Key Data Point | Year | Confidence |
|-------|--------|---------------|------|------------|
| K-Means on RFM is standard (K=8-15) | [ACM ICCIT 2025](https://dl.acm.org/doi/10.1145/3731763.3731805) + [RFM K-Means BIRCH 2024](https://www.researchgate.net/publication/382684957) | K-Means outperforms BIRCH on RFM; academic literature finds K=3-8 optimal (K=8-15 is enterprise practice) | 2024-2025 | High (K range caveat) |
| PCA before K-Means for high-dim features | [PMC/PLOS ONE 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11805403/) | "Customer segmentation data exhibits high correlations; PCA effectively represents various characteristics" | 2025 | High |
| Model size < 1 MB | Architectural derivation | 15 clusters × 10 features = 1,200 floats = ~9.6 KB; confirmed as "lightweight" in deployment guides | — | Moderate |
| 1M customers in < 60 sec | [scikit-learn KMeans docs](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html) | K-Means predict is O(kn) — fastest clustering inference; actual ~1-5 sec for 1M rows | 2024 | Moderate |
| T-SNE/PCA for cluster validation | [PMC 2025 — Dimensionality Reduction Review](https://pmc.ncbi.nlm.nih.gov/articles/PMC12453773/) + [GeeksforGeeks 2024](https://www.geeksforgeeks.org/machine-learning/difference-between-pca-vs-t-sne/) | t-SNE "ideal for visualizing clusters"; PCA for "global structure" | 2024-2025 | High |
| LLM-generated cluster names | [arXiv — k-LLMmeans (ICLR 2026)](https://arxiv.org/abs/2502.09667) + [LangLasso (arXiv 2025)](https://arxiv.org/abs/2601.10458) | "Summary-as-centroid retains k-means assignments while producing human-readable prototypes" | 2025 | High |
| Centroid checkpointing for longitudinal tracking | [MDPI — Concept Drift Detection 2024](https://www.mdpi.com/2078-2489/15/12/786) | Centroid-based methods reviewed for production ML drift monitoring | 2024 | Moderate |
| RFM as core features | [Shopify 2025](https://www.shopify.com/blog/rfm-analysis) + [Braze 2025](https://www.braze.com/resources/articles/rfm-segmentation) | "RFM reflects real shopping patterns"; "easier to apply and scale" | 2025 | High |
| GDPR deletion must propagate to CRM/email/ads | [GDPR Art. 17](https://gdpr-info.eu/art-17-gdpr/) + [Twilio Segment](https://www.twilio.com/en-us/recipes/streamline-gdpr-compliance-with-segment-end-user-privacy-tools) | "Controller must inform other controllers processing the data"; Segment auto-kicks deletions to all destinations | 2024-2025 | High |

### E. Dynamic Pricing — Sources

| Claim | Source | Key Data Point | Year | Confidence |
|-------|--------|---------------|------|------------|
| Hybrid ML elasticity (batch) + rule engine (real-time) | [IJCESEN paper](https://ijcesen.com/index.php/ijcesen/article/view/4981) + [42signals](https://www.42signals.com/blog/dynamic-pricing-models-ecommerce/) | "Rule-based constraint layers with ML models for demand elasticity estimation" | 2026 | High |
| Thompson Sampling bandit for price A/B | [MDPI Mathematics](https://www.mdpi.com/2227-7390/12/8/1123) + [IEEE Dynamic Pricing TS](https://ieeexplore.ieee.org/document/10486080) | Outperforms Laplace approx in convergence + regret; 4 TS variants implemented | 2024 | High |
| Price shock increases abandonment 15-25% | [MarketingLTB 2025](https://marketingltb.com/blog/statistics/cart-abandonment-rate-statistics/) + [Baymard Institute](https://baymard.com/lists/cart-abandonment-rate) | "Price mismatch raises abandonment by 21%"; 48% abandon due to unexpected costs | 2024-2025 | Moderate (21% is best cite) |
| Elasticity varies by SKU + competition | [Revology Analytics 2024](https://www.revologyanalytics.com/articles-insights/mastering-price-elasticity-modeling-best-practices-for-2024) | Only 28% of SKUs need close price parity; 3.1% GM gain from SKU-level modeling | 2024 | High |
| LightGBM for price elasticity estimation | [Sagepub — STL-GBM Model](https://journals.sagepub.com/doi/10.1177/14727978251338001) + [KDD 2025 Workshop](https://causal-machine-learning.github.io/kdd2025-workshop/papers/24.pdf) | STL-GBM for dynamic elasticity forecasting; debiased ML framework for price optimization | 2025 | High |
| Competitor monitoring: Prisync, Competera, Intelligence Node | [SuperAGI Comparison](https://web.superagi.com/ai-price-optimization-showdown-competera-vs-intelligence-node-vs-prisync-which-tool-reigns-supreme) | Intelligence Node: 10-second refresh, 99%+ accuracy, 1.2B+ SKUs tracked | 2025 | High |
| Cross-price elasticity weighted by competitor share | [Tredence](https://www.tredence.com/blog/win-the-cpg-price-wars-with-new-crossprice-elasticity-capabilities) | 1,200 pricing opportunities found at 90-95% accuracy; SKU-market cluster analysis | 2024 | Moderate |
| Dynamic pricing = margin optimizer | [AI CERTs](https://www.aicerts.ai/news/dynamic-pricing-algorithms-real-time-revenue-for-ecommerce/) + [Competera](https://competera.ai/resources/articles/ai-pricing-retail-industry-rulebook) | "Margins expand by as much as 10%"; Competera: 4.5% gross profit uplift | 2025-2026 | High |
| Price rendering < 50 ms | [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/How_long_is_too_long) | "Provide feedback within 100ms, preferably within 50ms" — general web standard, not pricing-specific | 2024 | Moderate |

---

## Cloudflare Workers + KV Evaluation

### Can Cloudflare Workers + KV replace AWS ECS + Redis for ML serving?

**Short answer: No for primary ML serving. Yes as an edge complement.**

#### Hard Blockers

| Constraint | Limit | Impact |
|-----------|-------|--------|
| **Worker memory** | 128 MB per isolate | Cannot load XGBoost (25 MB) + FAISS (35 MB) + Redis client + runtime overhead. Practical ceiling ~20-30 MB for model weights. |
| **KV eventual consistency** | Up to 60 seconds propagation | Fatal for velocity features (fraud detection requires features from <1 sec ago). Cannot use KV as a feature store. |
| **KV write rate** | 1 write/sec/key | Cannot sustain per-transaction ZADD writes for velocity features (need 5-15K writes/sec). |
| **KV write pricing** | $5.00/million writes | At 10K QPS fraud scoring → 864M writes/day → $4,320/day just for KV writes. |
| **No GPU** | Workers run V8 isolates only | Workers AI exists but is for LLMs/embeddings, not XGBoost/LightGBM. |
| **CPU time limit** | 30s default, 5 min max | ONNX inference for XGBoost in WASM: 50-300 ms CPU per prediction — workable but inefficient. |

Source: [Cloudflare Workers Limits](https://developers.cloudflare.com/workers/platform/limits/), [KV Pricing](https://developers.cloudflare.com/kv/platform/pricing/), [How KV Works](https://developers.cloudflare.com/kv/concepts/how-kv-works/)

#### Where Workers Could Complement AWS

| Use Case | Pattern | Benefit |
|----------|---------|---------|
| **Edge routing / auth** | Worker validates API key + rate limits → forwards to AWS ECS | Global edge PoPs reduce user-to-API latency by 20-50 ms |
| **Recommendation cache** | Worker checks KV for precomputed recs → cache miss routes to ECS | 70-80% cache hit rate offloads ECS; KV reads = $0.50/M |
| **A/B test routing** | Worker reads experiment config from KV → routes to model variant | Config changes infrequently, so 60s propagation is fine |
| **Response caching** | Worker caches pricing/reco responses by input hash → TTL 30-60s | Reduces QPS to origin by 50-80% during traffic spikes |

#### Cost Comparison at Scale (10K QPS, fraud scoring)

| Component | AWS (ECS + ElastiCache) | Cloudflare (Workers + KV) |
|-----------|------------------------|--------------------------|
| Compute | 5-8 c5.2xlarge = ~$1,200-1,900/mo | Workers: ~$150/mo (CPU-time billing) |
| Feature store | ElastiCache r6g.xlarge = ~$380/mo | KV writes: $4,320/day = ~$130K/mo (deal-breaker) |
| Model serving | Included in ECS | Cannot self-host; Workers AI doesn't support XGBoost |
| **Total** | **~$1,700-2,300/mo** | **~$130K+/mo** (KV write cost dominates) |

**Bottom line:** KV's write pricing ($5/M) makes it economically impossible as a real-time feature store. Workers + KV is 50-70x more expensive than AWS for write-heavy ML workloads. It works beautifully as a read-heavy caching layer on top of AWS.

Sources: [Cloudflare KV Pricing](https://developers.cloudflare.com/kv/platform/pricing/), [Baselime: 80% lower cost from AWS to CF](https://blog.cloudflare.com/80-percent-lower-cloud-cost-how-baselime-moved-from-aws-to-cloudflare/), [Workers vs Lambda cost comparison](https://www.vantage.sh/blog/cloudflare-workers-vs-aws-lambda-cost)

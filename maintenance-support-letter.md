# Memo: The Case for Post-Implementation Maintenance Engagements

**To:** phData Leadership
**From:** Brian Cohn, Principal Solutions Architect
**Date:** March 2026
**Re:** Why ML engagements should include structured maintenance offerings — and what that looks like

---

## Executive Summary

Every ML platform we deliver has a built-in expiration date on its accuracy. Unlike traditional software — where shipped code runs correctly until someone changes it — machine learning models degrade silently. Data drifts. Customer behavior shifts. Fraudsters adapt. Seasonal patterns rotate. The models we hand off today will underperform within 3–6 months without active maintenance.

This is not a flaw — it's the nature of statistical systems operating in dynamic environments. And it represents a significant, recurring revenue opportunity for phData.

I'm proposing that we formalize a **post-implementation maintenance offering** as a standard component of every ML engagement. Based on what I've seen across our case study portfolio and the work we're doing with clients like AwesomeStuff.com, the math is compelling: maintenance retainers generate ~$180–220K/yr per client at 70%+ margins, deepen our client relationships, and prevent the churn that happens when models degrade and clients blame the original build.

---

## Why ML Systems Are Not "Set and Forget"

Traditional software has deterministic behavior. If the code passes QA on Tuesday, it still passes on Friday. ML systems are fundamentally different — they're probabilistic, trained on historical data, and make assumptions about the future that erode over time.

Here are the specific failure modes I've observed, mapped to the five model types we commonly deploy:

### 1. Fraud Detection — Adversarial Drift

Fraudsters are not static. They observe which transactions get flagged and adapt their tactics. A fraud model trained on last quarter's attack patterns will miss next quarter's. This isn't hypothetical — it's documented across every major payment processor. Without regular retraining and threshold recalibration, false negative rates climb 15–30% within two quarters.

**What breaks:** Detection thresholds become stale. New fraud vectors emerge that fall outside the training distribution. False positive rates creep up, blocking legitimate customers and creating support burden.

### 2. Recommendation Engine — Catalog and Behavioral Churn

Product catalogs change constantly — new SKUs launch, old ones are discontinued, seasonal inventory rotates. A recommendation model trained on last season's purchase graph will push products that no longer exist or miss the items customers actually want. Meanwhile, user preferences shift with trends, marketing campaigns, and competitive dynamics.

**What breaks:** Cold-start problem for new products (no interaction history). Stale embeddings for discontinued items. Popularity bias amplifies as the model falls behind real-time behavior.

### 3. Inventory Forecasting — Distribution Shift

Supply chain conditions are volatile. A model trained during stable logistics will systematically misforecast when lead times change, new suppliers enter, or macro conditions shift (tariffs, shipping disruptions, raw material costs). New SKU categories require feature engineering that didn't exist at training time.

**What breaks:** Forecast confidence intervals widen. Stockout and overstock rates increase. The model can't account for structural changes it has never seen.

### 4. Customer Segmentation — Evolving Demographics

Customer bases are not static populations. Acquisition campaigns bring in new cohorts with different characteristics. Existing customers migrate between segments as their behavior changes. Marketing campaigns create feedback loops — the segments inform the campaigns, and the campaigns reshape the segments.

**What breaks:** Cluster boundaries become meaningless. High-value segments get diluted. Targeted campaigns lose precision because the underlying segments no longer reflect reality.

### 5. Dynamic Pricing — Market Response and Regulatory Exposure

Pricing models are uniquely sensitive to competitive dynamics. Competitors respond to your pricing changes, creating feedback loops the model wasn't trained to anticipate. Price elasticity estimates decay as market conditions shift. And regulatory scrutiny around algorithmic pricing is increasing — what was compliant at launch may not be compliant in 12 months.

**What breaks:** Margin erosion from stale elasticity estimates. Competitive response patterns the model doesn't recognize. Regulatory risk from pricing decisions that can't be explained or audited.

---

## The Revenue Opportunity

### What Maintenance Actually Looks Like

Based on the AwesomeStuff.com engagement and similar deployments across our portfolio, ongoing maintenance for a 5-model ML platform requires approximately **64 hours per month** of expert time:

| Activity | Frequency | Effort (hrs/mo) | Blended Rate | Monthly Cost |
|---|---|---|---|---|
| Model retraining & performance monitoring | Weekly | 20 | $225/hr | $4,500 |
| Infrastructure ops (ECS, Redis, ALB, CI/CD) | Ongoing | 16 | $200/hr | $3,200 |
| Security patching & CVE response | Weekly + on-demand | 8 | $225/hr | $1,800 |
| Feature engineering & model improvement | Monthly | 16 | $250/hr | $4,000 |
| Architecture review & capacity planning | Quarterly | 4 | $400/hr | $1,600 |
| **Total** | | **64** | | **$15,100/mo** |

That's **~$181K/yr in consulting revenue per client**, at margins significantly higher than net-new build work (no ramp-up, no discovery, no staffing risk — the team already knows the system).

### The Alternative: What Clients Face Without Us

When we hand off a platform and walk away after 30 days, the client has two options:

**Option A: Hire in-house.** An equivalent maintenance team requires at minimum 2 ML engineers ($200K+ each fully loaded) and fractional DevOps/MLOps support. Realistically, they're looking at $500K–700K/yr in headcount — plus 3–6 months to recruit and onboard, during which the models are degrading unmonitored.

**Option B: Do nothing.** The models run for 3–6 months, accuracy degrades, business stakeholders lose confidence in the platform, and the narrative becomes "the ML project failed." This damages our reputation and eliminates the expansion opportunity.

Neither option is good for the client or for us. A structured maintenance retainer is the third path.

### Scale Across the Portfolio

We have 76 published case studies. The majority involve ML or data platform deployments with ongoing maintenance needs. If we convert even 15–20% of completed engagements into maintenance retainers at $180K/yr average:

- **10 clients:** $1.8M/yr recurring revenue
- **15 clients:** $2.7M/yr recurring revenue
- **20 clients:** $3.6M/yr recurring revenue

This is high-margin, predictable revenue that compounds — maintenance clients don't churn the way project-based clients do, because the switching cost is the institutional knowledge of their specific platform.

---

## What I'm Proposing

### 1. Standardize a Maintenance Tier in Every ML Engagement

Every SOW for an ML build should include a section on post-implementation support options. Not as an upsell at the end — baked into the initial conversation. Clients should understand from day one that ML platforms require ongoing care, and we're the most cost-effective team to provide it (because we built it).

### 2. Three Engagement Tiers

| Tier | Hours/Month | Scope | Annual Cost |
|---|---|---|---|
| **Essential** | 24 | Monitoring, retraining, critical patches | ~$72K |
| **Standard** | 48 | Essential + infrastructure ops, feature engineering | ~$144K |
| **Premium** | 64+ | Standard + architecture reviews, model improvement, quarterly strategy | ~$181K+ |

### 3. Dedicated Maintenance Track for Solutions Architects

Maintenance work is different from build work. It requires deep system familiarity, pattern recognition across failure modes, and the judgment to distinguish between routine drift and structural model failure. This is senior work — not something to hand off to junior engineers. I'd recommend a lightweight specialization within the SA team for architects who manage ongoing client platforms.

### 4. Pilot with Current Engagements

Start with AwesomeStuff.com and 2–3 other clients approaching their 30-day post-handoff window. Offer a 6-month maintenance agreement at the Standard tier. Measure: time-to-detection for model degradation, client satisfaction, and revenue per architect-hour vs. build engagements.

---

## The Bottom Line

We're already doing the hardest part — building the platform, understanding the client's data, training the models. Walking away after handoff leaves recurring revenue on the table and exposes our delivered work to degradation that we'll eventually get blamed for.

A structured maintenance offering protects our reputation, deepens client relationships, and generates predictable, high-margin revenue. ML models need ongoing care. We should be the ones providing it.

---

*Brian Cohn*
*Principal Solutions Architect*

#!/usr/bin/env python3
"""FastAPI backend for phData Experience Portal - serves API + React frontend."""

import sqlite3
import os
import re
import math
import subprocess
from collections import Counter
from fastapi import FastAPI, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from rank_bm25 import BM25Okapi

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phdata_cases.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = FastAPI(title="phData Experience Portal", version="1.0.0")

# --- BM25 Engine ---

STOPWORDS = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
             "of", "with", "by", "from", "is", "was", "are", "were", "been", "be",
             "have", "has", "had", "do", "does", "did", "will", "would", "could",
             "should", "may", "might", "shall", "can", "this", "that", "these",
             "those", "it", "its", "they", "their", "them", "we", "our", "us"}

def tokenize(text):
    tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


class SearchEngine:
    def __init__(self):
        self.documents = []
        self.bm25 = None
        self._load()

    def _load(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM case_studies ORDER BY id")
        self.documents = [dict(row) for row in c.fetchall()]
        conn.close()

        corpus = []
        for doc in self.documents:
            combined = " ".join([
                doc.get("title", "") or "",
                doc.get("client", "") or "",
                doc.get("industry", "") or "",
                doc.get("challenge", "") or "",
                doc.get("solution", "") or "",
                doc.get("results", "") or "",
                doc.get("technologies", "") or "",
                doc.get("full_text", "") or "",
            ])
            corpus.append(tokenize(combined))
        self.bm25 = BM25Okapi(corpus)

    def search(self, query, top_k=20):
        tokens = tokenize(query)
        scores = self.bm25.get_scores(tokens)
        scored = list(zip(scores, self.documents))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:top_k]:
            if score > 0:
                results.append({**doc, "score": round(score, 4), "scraped_at": str(doc.get("scraped_at", ""))})
        return results


engine = SearchEngine()


# --- API Routes ---

@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=50)):
    results = engine.search(q, top_k=limit)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/case-studies")
def list_case_studies(
    industry: str = Query(None),
    limit: int = Query(76, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    docs = engine.documents
    if industry:
        docs = [d for d in docs if (d.get("industry") or "").lower() == industry.lower()]
    total = len(docs)
    docs = docs[offset:offset + limit]
    return {"total": total, "count": len(docs), "results": [
        {**d, "scraped_at": str(d.get("scraped_at", ""))} for d in docs
    ]}


@app.get("/api/case-studies/{case_id}")
def get_case_study(case_id: int):
    for doc in engine.documents:
        if doc["id"] == case_id:
            return {**doc, "scraped_at": str(doc.get("scraped_at", ""))}
    return JSONResponse(status_code=404, content={"error": "Not found"})


@app.get("/api/stats")
def stats():
    industries = {}
    technologies = {}
    for doc in engine.documents:
        ind = (doc.get("industry") or "Unknown").strip()
        industries[ind] = industries.get(ind, 0) + 1
        for tech in (doc.get("technologies") or "").split(", "):
            tech = tech.strip()
            if tech:
                technologies[tech] = technologies.get(tech, 0) + 1

    return {
        "total_case_studies": len(engine.documents),
        "industries": sorted(industries.items(), key=lambda x: x[1], reverse=True),
        "technologies": sorted(technologies.items(), key=lambda x: x[1], reverse=True),
    }


@app.get("/api/brian-fit")
def brian_fit():
    """Return pre-computed Brian Cohn fit analysis."""
    top_10_interesting = [
        {"rank": 1, "title": "Restaurant Chain Streamlines IT Resolution Using Generative AI", "score": 82, "industry": "Restaurant & Food Service", "why": "RAG-powered conversational AI serving 2,700+ locations with 30x faster resolution"},
        {"rank": 2, "title": "Legal Services Provider Transforms Staffing with XGBoost & Prophet", "score": 77, "industry": "Legal Services", "why": "ML forecasting (XGBoost + Prophet) achieving 80% accuracy on 12-week demand predictions"},
        {"rank": 3, "title": "Leading Learning Platform Utilizes AI Applications", "score": 71, "industry": "Education Technology", "why": "Modular AI assistant platform with Claude Sonnet, feature stores, and orchestration"},
        {"rank": 4, "title": "Order.co Accelerates Automation with Agentic AI on AWS", "score": 70, "industry": "Technology", "why": "Cutting-edge agentic AI with Amazon Nova-Act achieving 100% success across vendors"},
        {"rank": 5, "title": "Healthcare Tech Revenue Cycle Prediction with Snowpark + ML", "score": 67, "industry": "Healthcare", "why": "20-hour to 13-minute runtime reduction with 20x cost savings via ML optimization"},
        {"rank": 6, "title": "FSI Giant Uses RAG AI Chatbot for Contract Inquiries", "score": 65, "industry": "Financial Services", "why": "RAG chatbot saving $400K/year with <5 second retrieval replacing 3-day manual process"},
        {"rank": 7, "title": "EdTech Firm Saves Millions with Knowledge Graphs and AI", "score": 54, "industry": "Education Technology", "why": "Knowledge graphs + GenAI reducing course creation cost by 80% ($120K to $15K)"},
        {"rank": 8, "title": "US Telecom Giant ML Feature Store + Snowflake", "score": 48, "industry": "Telecommunications", "why": "Enterprise ML infrastructure with Feast Framework, centralized feature management"},
        {"rank": 9, "title": "Medical Company Uses ML for Sleep Apnea Technology", "score": 48, "industry": "Healthcare", "why": "MLOps platform with LSTM, CNN, XGBoost for medical device signal processing"},
        {"rank": 10, "title": "Financial Services Contract Inquiry Efficiency on AWS", "score": 43, "industry": "Financial Services", "why": "Amazon Kendra NLP search + Step Functions achieving 70% response time reduction"},
    ]
    top_5_contribution = [
        {"rank": 1, "title": "Legal Services Provider - XGBoost & Prophet Staffing", "score": 91, "industry": "Legal Services", "match": "Direct ML model expertise (XGBoost, Prophet, SageMaker) + AWS pipeline architecture"},
        {"rank": 2, "title": "Restaurant Chain - GenAI IT Resolution", "score": 83, "industry": "Restaurant & Food Service", "match": "GenAI/RAG architecture + LLM deployment expertise from Credera/AstraZeneca work"},
        {"rank": 3, "title": "Medical Company - Sleep Apnea ML", "score": 83, "industry": "Healthcare", "match": "Medical device domain + ML/signal processing + clinical trial experience as NIH PI"},
        {"rank": 4, "title": "Healthcare Tech - Revenue Cycle Prediction", "score": 77, "industry": "Healthcare", "match": "Healthcare domain expertise + ML optimization + Python/Snowpark engineering"},
        {"rank": 5, "title": "FSI Giant - RAG AI Chatbot", "score": 68, "industry": "Financial Services", "match": "RAG/LLM architecture + AWS pipeline (Lambda, Bedrock) + production AI deployment"},
    ]
    return {"top_10_interesting": top_10_interesting, "top_5_contribution": top_5_contribution}


PROSPECTS = [
    # --- CO-Headquartered: Medical Devices ---
    {"id": 1, "name": "Terumo Blood and Cell Technologies", "type": "Medical Device", "county": "Denver",
     "lat": 39.7105, "lng": -105.0811, "address": "10810 W Collins Ave, Lakewood, CO 80215",
     "url": "https://www.terumobct.com/", "logo": "terumo-bct",
     "revenue": "$1.5B", "employees": "7,900+ globally",
     "opportunity": "Cell therapy manufacturing data integration across Quantum Flex, Finia, and Cadence/Vista software systems; ML-driven blood component yield optimization across $250M Douglas County facility.",
     "projects": 5, "tags": ["ML", "IoT", "Data Platform", "Analytics", "Automation"],
     "rationale": "Global HQ in Lakewood with 7,900+ employees. Actively hiring DevOps and Software Engineers. Cadence Data Collection and Vista Information Systems generate manufacturing process data across blood banking and cell/gene therapy platforms, creating direct need for data pipeline unification and ML optimization."},
    {"id": 2, "name": "CoorsTek", "type": "Medical Device", "county": "Denver",
     "lat": 39.7555, "lng": -105.2211, "address": "14143 Denver West Pkwy, Golden, CO 80401",
     "url": "https://www.coorstek.com/", "logo": "coorstek",
     "revenue": "$1.6B", "employees": "7,000+",
     "opportunity": "SAP ERP implementation and Model Plant initiative support; manufacturing analytics across Wonderware/Azure infrastructure to unify quality and supply chain data across global ceramics operations.",
     "projects": 4, "tags": ["ML", "Data Platform", "Analytics", "Automation"],
     "rationale": "HQ in Golden, building new 182,000 sq ft headquarters (completion early 2026). Actively hiring SAP Business Analysts and Demand Planners requiring SAP IBP. Model Plant initiative focused on operator efficiency and ERP readiness is a direct fit for phData's data platform and analytics consulting."},
    {"id": 3, "name": "ZimVie", "type": "Medical Device", "county": "Denver",
     "lat": 39.8861, "lng": -105.0769, "address": "10225 Westmoor Dr, Westminster, CO 80021",
     "url": "https://www.zimvie.com/", "logo": "zimvie",
     "revenue": "$914M", "employees": "2,600+",
     "opportunity": "Dental implant outcomes analytics, manufacturing quality ML, commercial analytics, customer engagement GenAI",
     "projects": 4, "tags": ["ML", "Analytics", "Data Platform", "GenAI"],
     "rationale": "Spun off from Zimmer Biomet in 2022, HQ'd in Westminster. Dental medical devices. Post-spinoff data infrastructure buildout represents a greenfield opportunity for phData's full data platform stack."},
    {"id": 4, "name": "Paragon 28", "type": "Medical Device", "county": "Denver",
     "lat": 39.5838, "lng": -104.8771, "address": "14445 Grasslands Dr, Englewood, CO 80112",
     "url": "https://www.paragon28.com/", "logo": "paragon28",
     "revenue": "$256M", "employees": "800+",
     "opportunity": "Foot/ankle surgical device analytics, surgeon outcome tracking ML, inventory optimization, commercial intelligence platform",
     "projects": 4, "tags": ["ML", "Analytics", "Data Platform", "Supply Chain"],
     "rationale": "NYSE-listed (FNA), HQ'd in Englewood. Exclusively focused on foot and ankle orthopedics — fracture fixation, forefoot correction, ankle procedures. Surgeon outcome data and inventory analytics are high-value use cases."},
    {"id": 5, "name": "Zynex Medical", "type": "Medical Device", "county": "Denver",
     "lat": 39.5651, "lng": -104.8770, "address": "9655 Maroon Cir, Englewood, CO 80112",
     "url": "https://www.zynexmed.com/", "logo": "zynex-medical",
     "revenue": "$192M (FY2024)", "employees": "1,000+",
     "opportunity": "⚠ At Risk: Filed Chapter 11 bankruptcy Dec 2025 following Tricare payment suspension. Post-restructuring data needs may emerge if company exits bankruptcy.",
     "projects": 1, "tags": ["IoT", "Data Pipeline", "Analytics"],
     "rationale": "Filed Chapter 11 Dec 2025 after Tricare (20-25% of revenue) suspended payments. Delisted from NASDAQ Dec 24, 2025. Settled federal billing investigation Feb 2026. This prospect should be deprioritized until restructuring completes."},
    {"id": 6, "name": "Vivos Therapeutics", "type": "Medical Device", "county": "Denver",
     "lat": 39.6133, "lng": -105.0166, "address": "7921 Southpark Plaza, Littleton, CO 80120",
     "url": "https://www.vivos.com/", "logo": "vivos",
     "revenue": "$15M", "employees": "100+",
     "opportunity": "Sleep apnea treatment outcome analytics, provider network optimization, patient engagement GenAI, clinical evidence platform",
     "projects": 3, "tags": ["ML", "Analytics", "GenAI", "Data Platform"],
     "rationale": "NASDAQ-listed (VVOS), HQ'd in Littleton. FDA-cleared oral devices for sleep apnea. Treatment outcome data and provider network analytics align directly with phData's healthcare ML case studies."},
    {"id": 7, "name": "PharmaJet", "type": "Medical Device", "county": "Denver",
     "lat": 39.7555, "lng": -105.2200, "address": "1780 55th St, Golden, CO 80401",
     "url": "https://www.pharmajet.com/", "logo": "pharmajet",
     "revenue": "$6.3M", "employees": "50+",
     "opportunity": "Needle-free injection device IoT tracking, global vaccine deployment analytics, WHO partnership data platform, supply chain forecasting",
     "projects": 3, "tags": ["IoT", "Analytics", "Data Platform", "Supply Chain"],
     "rationale": "HQ'd in Golden. 12M+ vaccine injections worldwide using needle-free Tropis system. WHO contract for global distribution. Device deployment and supply chain data ideal for phData's analytics expertise."},
    {"id": 8, "name": "TriSalus Life Sciences", "type": "Medical Device", "county": "Denver",
     "lat": 39.8861, "lng": -105.0769, "address": "6272 W 91st Ave, Westminster, CO 80031",
     "url": "https://www.trisaluslifesci.com/", "logo": "trisalus",
     "revenue": "$29M", "employees": "200+",
     "opportunity": "Oncology drug delivery analytics, TriNav clinical outcomes ML, immunotherapy response prediction, real-world evidence platform",
     "projects": 3, "tags": ["ML", "Analytics", "Data Platform", "GenAI"],
     "rationale": "NASDAQ-listed (TLSI), HQ'd in Westminster. 59% YoY revenue growth. TriNav infusion system for liver/pancreatic tumors generates clinical outcome data ideal for ML-driven treatment optimization."},

    # --- CO-Headquartered: Pharma / CDMO ---
    {"id": 9, "name": "Tolmar", "type": "Pharma", "county": "Denver",
     "lat": 40.5853, "lng": -105.0844, "address": "701 Centre Ave, Fort Collins, CO 80526",
     "url": "https://www.tolmar.com/", "logo": "tolmar",
     "revenue": "$236M", "employees": "~1,000",
     "opportunity": "Manufacturing data platform for 340,000+ sq ft cGMP facilities across Fort Collins and Windsor CO; process optimization ML for long-acting injectable formulation (Eligard) production lines.",
     "projects": 4, "tags": ["ML", "Data Platform", "Analytics", "NLP"],
     "rationale": "Global HQ in Fort Collins with ~1,000 employees across 4 continents. Operates 340,000+ sq ft of cGMP manufacturing including new 225,000 sq ft Windsor CO site. Long-acting injectable drug delivery specialization creates demand for unified data platforms and yield optimization."},
    {"id": 10, "name": "CordenPharma Colorado", "type": "Pharma / CDMO", "county": "Denver",
     "lat": 40.0150, "lng": -105.2705, "address": "2075 55th St, Boulder, CO 80301",
     "url": "https://www.cordenpharma.com/", "logo": "cordenpharma",
     "revenue": "$110M (site)", "employees": "700+ (growing to 900+)",
     "opportunity": "Data infrastructure for $500M Boulder site expansion doubling SPPS reactor capacity to 42,000+ liters by 2028; batch process ML and yield optimization for GLP-1 peptide manufacturing across EUR 3B in long-term contracts.",
     "projects": 5, "tags": ["ML", "Data Platform", "IoT", "Analytics", "Supply Chain"],
     "rationale": "Boulder site is one of the world's largest peptide API manufacturing facilities, part of CordenPharma's EUR 900M global peptide platform investment. Expansion adds 25,000L of SPPS capacity and 200+ new employees. Hiring Associate Director of Business Intelligence and Master Data Specialists."},
    {"id": 11, "name": "Aytu BioPharma", "type": "Pharma", "county": "Denver",
     "lat": 39.5838, "lng": -104.8771, "address": "373 Inverness Pkwy, Englewood, CO 80112",
     "url": "https://www.aytubio.com/", "logo": "aytu",
     "revenue": "$66M", "employees": "150+",
     "opportunity": "ADHD prescription analytics, patient adherence ML, commercial data platform, regulatory submission automation",
     "projects": 3, "tags": ["ML", "Analytics", "Data Platform", "NLP"],
     "rationale": "NASDAQ-listed (AYTU), HQ'd in Englewood. Specialty pharma focused on ADHD treatments (Adhansia XR, Cotempla XR-ODT). Patient adherence data and commercial analytics are direct phData strengths."},

    # --- CO-Headquartered: Diagnostics / Biotech ---
    {"id": 12, "name": "Heska Corporation", "type": "Diagnostics", "county": "Denver",
     "lat": 40.4372, "lng": -105.0708, "address": "3760 Rocky Mountain Ave, Loveland, CO 80538",
     "url": "https://www.heska.com/", "logo": "heska",
     "revenue": "$257M", "employees": "360+",
     "opportunity": "Post-Mars acquisition integration of Heska's cloud-based diagnostic data archival with Antech Diagnostics' reference lab platform; ML for veterinary point-of-care instrument fleet management and digital cytology services.",
     "projects": 3, "tags": ["ML", "IoT", "Data Platform", "Analytics"],
     "rationale": "Loveland HQ acquired by Mars for $1.3B in June 2023, now part of Mars Science & Diagnostics alongside Antech. Portfolio spans POC lab instruments, digital radiography, cloud-based data management, PIMS software, and digital cytology. Antech-Heska data platform integration is a significant data engineering opportunity."},
    {"id": 13, "name": "Biodesix", "type": "Diagnostics", "county": "Denver",
     "lat": 39.9778, "lng": -105.1319, "address": "2970 Wilderness Pl, Boulder, CO 80301",
     "url": "https://www.biodesix.com/", "logo": "biodesix",
     "revenue": "$71M (FY2024)", "employees": "350+",
     "opportunity": "Scaling data infrastructure for 80,000 sq ft Louisville HQ/lab; ML pipeline buildout for Nodify Lung and IQLung test platforms processing 54,300+ annual test volumes with 45% YoY growth.",
     "projects": 4, "tags": ["ML", "Genomics", "Data Pipeline", "Analytics", "GenAI"],
     "rationale": "NASDAQ-listed (BDSX), relocated to Louisville CO in Jan 2024. Revenue grew 45% in FY2024 to $71.3M with 78% gross margins. Hiring Senior Software Engineers and BI Developers. Rapid test volume growth demands scalable data pipelines for proteomic and genomic diagnostic data."},
    {"id": 14, "name": "SomaLogic (Illumina)", "type": "Diagnostics / Biotech", "county": "Denver",
     "lat": 40.0150, "lng": -105.2519, "address": "2795 E Cottonwood Pkwy, Boulder, CO 80301",
     "url": "https://somalogic.com/", "logo": "illumina",
     "revenue": "$425M acquisition", "employees": "250+",
     "opportunity": "Post-acquisition data platform integration: unifying SomaScan proteomics assay data (7,000+ proteins) with Illumina's NGS/DRAGEN pipelines and Connected Multiomics platform for ~40 early-access customers.",
     "projects": 4, "tags": ["ML", "Genomics", "Data Platform", "Analytics"],
     "rationale": "Boulder CLIA/CAP-certified lab acquired by Illumina for $425M (Jan 2026). Integration of SomaScan, Illumina Protein Prep, SomaSignal Tests, and DRAGEN software into a unified multiomics platform creates massive data engineering needs. Illumina expects profitability by 2027."},
    {"id": 15, "name": "Cerapedics", "type": "Biotech", "county": "Denver",
     "lat": 39.8861, "lng": -105.0769, "address": "4025 Automation Way, Westminster, CO 80031",
     "url": "https://www.cerapedics.com/", "logo": "cerapedics",
     "revenue": "$55M", "employees": "150+",
     "opportunity": "Clinical trial data analytics, i-FACTOR outcomes tracking, regulatory submission automation, surgeon adoption ML",
     "projects": 3, "tags": ["Data Platform", "Analytics", "NLP", "ML"],
     "rationale": "HQ'd in Westminster. FDA PMA-approved i-FACTOR bone graft for spinal fusion. $180M total funding. Clinical trial outcomes data and regulatory submission workflows are strong consulting entry points."},
    {"id": 16, "name": "Foresight Diagnostics", "type": "Diagnostics", "county": "Denver",
     "lat": 40.0274, "lng": -105.2519, "address": "2801 Wilderness Pl, Boulder, CO 80301",
     "url": "https://www.foresight-dx.com/", "logo": "foresight",
     "revenue": "$7M", "employees": "80+",
     "opportunity": "Cancer MRD liquid biopsy data pipeline, genomic analytics platform, clinical validation ML, CLIA lab data management",
     "projects": 3, "tags": ["ML", "Genomics", "Data Pipeline", "Analytics"],
     "rationale": "HQ'd in Boulder. $86M raised. Foresight CLARITY liquid biopsy platform detects minimal residual disease with ultra-high sensitivity. Genomic data pipelines and clinical validation analytics are direct phData fits."},
    {"id": 17, "name": "Flagship Biosciences", "type": "Diagnostics", "county": "Denver",
     "lat": 39.9205, "lng": -105.0867, "address": "4785 Walnut St, Boulder, CO 80301",
     "url": "https://www.flagshipbio.com/", "logo": "flagship",
     "revenue": "$16M", "employees": "100+",
     "opportunity": "Spatial biology AI platform, tissue image analysis ML, pharma trial biomarker analytics, clinical data management",
     "projects": 3, "tags": ["ML", "Analytics", "GenAI", "Data Platform"],
     "rationale": "HQ'd in Broomfield. Patented imaging + AI technology for tissue sample analysis. Serves pharma clients in clinical trials. Spatial biology data pipelines and ML-powered image analytics are high-growth phData opportunities."},
    {"id": 18, "name": "Corgenix Medical", "type": "Diagnostics", "county": "Denver",
     "lat": 39.9205, "lng": -105.0250, "address": "11575 Main St, Broomfield, CO 80020",
     "url": "https://www.corgenix.com/", "logo": "corgenix",
     "revenue": "$8M", "employees": "50+",
     "opportunity": "Diagnostic test kit manufacturing analytics, immunology data platform, quality assurance automation, global distribution tracking",
     "projects": 2, "tags": ["Analytics", "Data Platform", "Automation"],
     "rationale": "HQ'd in Broomfield (Sebia Group). 50+ diagnostic test kits for immunology, vascular diseases, and viral hemorrhagic diseases. Manufacturing analytics and global distribution tracking are consulting entry points."},

    # --- CO-Headquartered: Clinical-Stage Biotech ---
    {"id": 19, "name": "Edgewise Therapeutics", "type": "Biotech", "county": "Denver",
     "lat": 40.0274, "lng": -105.2519, "address": "3415 Colorado Ave, Boulder, CO 80303",
     "url": "https://www.edgewisetx.com/", "logo": "edgewise",
     "revenue": "$1.9B mkt cap", "employees": "100+",
     "opportunity": "Clinical trial data platform, Phase 3 analytics pipeline, patient stratification ML, regulatory submission GenAI",
     "projects": 3, "tags": ["ML", "Data Platform", "Analytics", "GenAI"],
     "rationale": "NASDAQ-listed (EWTX), HQ'd in Boulder. $563M cash. Lead candidate sevasemten in Phase 3 for muscular dystrophy and cardiac diseases. Clinical trial data infrastructure buildout is a major consulting opportunity."},
    {"id": 20, "name": "OnKure Therapeutics", "type": "Biotech", "county": "Denver",
     "lat": 40.0150, "lng": -105.2705, "address": "2530 55th St, Boulder, CO 80301",
     "url": "https://www.onkuretherapeutics.com/", "logo": "onkure",
     "revenue": "$55M raised", "employees": "50+",
     "opportunity": "Precision oncology trial analytics, PI3K-alpha mutation data platform, patient matching ML, drug discovery pipeline",
     "projects": 2, "tags": ["ML", "Data Platform", "Analytics", "Genomics"],
     "rationale": "NASDAQ-listed (OKUR), HQ'd in Boulder. Precision oncology targeting PI3K-alpha mutations. Clinical trial and genomic data management needs align with phData's data engineering and ML platform capabilities."},
]


@app.get("/api/prospects")
def get_prospects():
    total_projects = sum(p["projects"] for p in PROSPECTS)
    by_type = {}
    by_county = {}
    for p in PROSPECTS:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1
        by_county[p["county"]] = by_county.get(p["county"], 0) + 1
    return {
        "prospects": PROSPECTS,
        "stats": {
            "total": len(PROSPECTS),
            "total_projects": total_projects,
            "by_type": sorted(by_type.items(), key=lambda x: x[1], reverse=True),
            "by_county": by_county,
        },
    }


@app.post("/api/name-clusters")
@app.post("/api/name-cluster")
async def name_cluster(payload: dict = Body(...)):
    """Call claude -p to name a single cluster. Frontend calls once per cluster for streaming UX."""
    cid = payload.get("id", 0)
    titles = payload.get("titles", [])
    titles_str = "\n".join(f"- {t}" for t in titles)
    prompt = (
        f"Given these case study titles from a data analytics consulting firm, "
        f"generate a short 2-4 word thematic label for this cluster. "
        f"Return ONLY the label, nothing else. No quotes, no explanation.\n\n{titles_str}"
    )
    try:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=30, env=env
        )
        name = result.stdout.strip()
        if not name or len(name) > 50:
            name = f"Cluster {cid + 1}"
    except Exception:
        name = f"Cluster {cid + 1}"
    return {"id": cid, "label": name}


@app.get("/api/vectors")
def vectors():
    """Return TF-IDF vectors for all case studies (for t-SNE in browser)."""
    docs = engine.documents
    # Build corpus of token lists
    corpus_tokens = []
    for doc in docs:
        combined = " ".join([
            doc.get("title", "") or "",
            doc.get("client", "") or "",
            doc.get("industry", "") or "",
            doc.get("challenge", "") or "",
            doc.get("solution", "") or "",
            doc.get("results", "") or "",
            doc.get("technologies", "") or "",
            doc.get("full_text", "") or "",
        ])
        corpus_tokens.append(tokenize(combined))

    # Build vocabulary from top terms by document frequency
    df = Counter()
    for tokens in corpus_tokens:
        for t in set(tokens):
            df[t] += 1
    # Filter: appear in at least 2 docs, at most 90% of docs
    n = len(docs)
    vocab = [t for t, count in df.most_common() if 2 <= count <= int(n * 0.9)]
    vocab = vocab[:200]  # Cap at 200 dimensions for browser perf
    vocab_idx = {t: i for i, t in enumerate(vocab)}

    # Compute TF-IDF
    result = []
    for i, tokens in enumerate(corpus_tokens):
        tf = Counter(tokens)
        total = len(tokens) if tokens else 1
        vec = []
        for term in vocab:
            tf_val = tf.get(term, 0) / total
            idf_val = math.log(n / (df[term] + 1)) + 1
            vec.append(round(tf_val * idf_val, 6))
        doc = docs[i]
        result.append({
            "id": doc["id"],
            "title": doc.get("title", ""),
            "industry": doc.get("industry", "Unknown"),
            "technologies": doc.get("technologies", ""),
            "vector": vec,
        })

    return {"vocab_size": len(vocab), "num_docs": len(result), "documents": result}


# --- Static Files (React Frontend) ---

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/{full_path:path}")
def serve_spa(full_path: str = ""):
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

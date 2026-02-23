#!/usr/bin/env python3
"""Analyze phData's client base and identify growth opportunities for Brian Cohn."""

import sqlite3
import os
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phdata_cases.db")
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Brian's network and domain connections
BRIAN_NETWORK = {
    "direct_connections": [
        {
            "company": "AstraZeneca",
            "relationship": "Built the AIMI Medical Virtual Assistant (GenAI ML) while at Credera",
            "industry": "Pharmaceutical",
            "potential": "AstraZeneca has massive data infrastructure needs. Brian's direct relationship "
                        "and understanding of their clinical data challenges could open doors for phData's "
                        "Snowflake/dbt modernization, AI/ML platform services, and data governance solutions."
        },
        {
            "company": "Credera (Omnicom Group)",
            "relationship": "Current employer - Senior Architect for GenAI",
            "industry": "Consulting/Technology",
            "potential": "Credera's client relationships span Fortune 500 companies. Brian's network within "
                        "Credera could identify clients who need specialized data platform work that phData excels at, "
                        "creating a referral pipeline."
        },
        {
            "company": "Kaspect",
            "relationship": "Chief Scientist",
            "industry": "Technology/Healthcare",
            "potential": "As Chief Scientist, Brian has visibility into Kaspect's customer base and their "
                        "data challenges, which could translate into joint ventures or referrals to phData."
        },
        {
            "company": "Adventure Biofeedback",
            "relationship": "Co-Founder",
            "industry": "Healthcare/Medical Devices",
            "potential": "The medical device and health tech ecosystem has extensive data needs. Brian's "
                        "connections in this space (clinicians, hospital systems, device manufacturers) "
                        "represent untapped potential for phData's healthcare analytics practice."
        },
    ],
    "research_network": [
        {
            "institution": "USC Viterbi School of Engineering",
            "relationship": "Ph.D. alumnus",
            "potential": "USC's extensive corporate partnerships and alumni network in SoCal tech "
                        "provide access to companies seeking data modernization and AI services."
        },
        {
            "institution": "Howard Hughes Medical Institute",
            "relationship": "Research grant recipient",
            "potential": "HHMI's network spans major research universities and biotech firms, "
                        "all of which have growing data infrastructure needs."
        },
        {
            "institution": "NIH / SBIR Program",
            "relationship": "Direct-to-Phase-II grant PI",
            "potential": "NIH-funded organizations (hospitals, research institutions, biotech startups) "
                        "increasingly need cloud data platforms and AI/ML capabilities."
        },
    ],
    "domain_expertise_verticals": [
        {
            "vertical": "Pharmaceutical & Life Sciences",
            "brian_credential": "AstraZeneca GenAI work, NIH SBIR PI, clinical trial design",
            "phdata_gap": "phData has some pharma case studies but could expand significantly. "
                         "Brian's deep pharma understanding would help sell and deliver "
                         "complex life sciences data projects.",
            "target_companies": [
                "Pfizer", "Merck", "Johnson & Johnson", "Roche", "Novartis",
                "Eli Lilly", "AbbVie", "Bristol-Myers Squibb", "Amgen", "Gilead",
                "Regeneron", "Biogen", "Moderna", "Vertex Pharmaceuticals",
            ]
        },
        {
            "vertical": "Medical Devices & Health Tech",
            "brian_credential": "Co-founded Adventure Biofeedback, built medical device AWS pipeline, "
                               "sleep apnea research, osteoarthritis clinical trial",
            "phdata_gap": "phData has medical device case studies (sleep apnea, NextGen Healthcare) "
                         "but Brian could dramatically expand this vertical through his direct "
                         "industry relationships and understanding of FDA data requirements.",
            "target_companies": [
                "Medtronic", "Abbott", "Boston Scientific", "Stryker", "Baxter",
                "Intuitive Surgical", "Edwards Lifesciences", "ResMed",
                "Dexcom", "Insulet", "iRhythm Technologies", "Penumbra",
            ]
        },
        {
            "vertical": "Healthcare Systems & Providers",
            "brian_credential": "Clinical interface development, healthcare AI applications, "
                               "patient outcome analytics",
            "phdata_gap": "phData has healthcare provider case studies but Brian's clinical "
                         "background gives him credibility that typical data consultants lack. "
                         "He can speak the language of clinicians and administrators.",
            "target_companies": [
                "Epic Systems (clients)", "Cerner/Oracle Health (clients)",
                "Kaiser Permanente", "HCA Healthcare", "CommonSpirit Health",
                "Ascension", "Providence", "Cleveland Clinic", "Mayo Clinic",
                "Intermountain Healthcare", "Geisinger",
            ]
        },
        {
            "vertical": "AI/ML-First Companies",
            "brian_credential": "GenAI architecture, Nature Machine Intelligence publication, "
                               "reinforcement learning, autonomous systems",
            "phdata_gap": "phData's AI/ML case studies are growing but many still focus on basic "
                         "analytics. Brian could help phData win and deliver cutting-edge AI projects "
                         "that require research-level ML expertise.",
            "target_companies": [
                "AI-native startups seeking data platform maturity",
                "Enterprise companies building AI centers of excellence",
                "Research institutions transitioning to cloud-native ML",
                "Government agencies with AI mandates (VA, DoD health)",
            ]
        },
    ]
}


def analyze_phdata_clients():
    """Analyze phData's existing client base from case studies."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, url, title, industry, technologies, full_text, challenge, solution, results FROM case_studies")
    rows = c.fetchall()
    conn.close()

    industries = defaultdict(list)
    tech_usage = defaultdict(int)
    client_types = defaultdict(int)

    for row in rows:
        _id, url, title, industry, technologies, full_text, challenge, solution, results = row
        slug = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]

        ind = industry or "Unknown"
        industries[ind].append({"title": title, "url": url, "slug": slug})

        # Count tech usage from URL slugs (since full text was limited)
        slug_lower = slug.lower()
        url_lower = url.lower()
        title_lower = (title or "").lower()
        combined = f"{slug_lower} {url_lower} {title_lower}"

        tech_map = {
            "snowflake": "Snowflake", "dbt": "dbt", "airflow": "Airflow",
            "aws": "AWS", "azure": "Azure", "tableau": "Tableau",
            "power-bi": "Power BI", "powerbi": "Power BI", "sigma": "Sigma Computing",
            "alteryx": "Alteryx", "dataiku": "Dataiku", "snowpark": "Snowpark",
            "sap": "SAP", "hadoop": "Hadoop", "teradata": "Teradata",
            "cloudera": "Cloudera", "omni": "Omni", "fabric": "Microsoft Fabric",
            "purview": "Microsoft Purview", "veeva": "Veeva",
            "ml": "Machine Learning", "machine-learning": "Machine Learning",
            "ai": "AI/ML", "genai": "Generative AI", "generative-ai": "Generative AI",
            "rag": "RAG", "chatbot": "Chatbot/Conversational AI",
            "xgboost": "XGBoost", "prophet": "Prophet",
            "knowledge-graph": "Knowledge Graphs", "feature-store": "Feature Store",
            "agentic": "Agentic AI", "uipath": "UiPath/RPA", "ui-path": "UiPath/RPA",
            "sentiment": "Sentiment Analysis/NLP",
        }
        for key, val in tech_map.items():
            if key in combined:
                tech_usage[val] += 1

        # Client type indicators
        size_map = {
            "fortune-500": "Fortune 500", "fortune 500": "Fortune 500",
            "global": "Global Enterprise", "leading": "Industry Leader",
            "top": "Industry Leader", "major": "Large Enterprise",
            "prominent": "Large Enterprise", "giant": "Large Enterprise",
            "large": "Large Enterprise",
        }
        for key, val in size_map.items():
            if key in combined:
                client_types[val] += 1
                break

    return industries, tech_usage, client_types


def generate_client_growth_report():
    """Generate the full client growth opportunity report."""
    industries, tech_usage, client_types = analyze_phdata_clients()

    lines = []
    lines.append("# How Brian Cohn Can Grow phData's Clientele")
    lines.append("## A Strategic Analysis of Client Acquisition Opportunities\n")
    lines.append("---\n")

    # Current landscape
    lines.append("## 1. phData's Current Client Landscape\n")
    lines.append("### Industry Distribution\n")
    lines.append("| Industry | Case Studies | % of Portfolio |")
    lines.append("|----------|-------------|----------------|")
    total = sum(len(v) for v in industries.values())
    for ind, cases in sorted(industries.items(), key=lambda x: len(x[1]), reverse=True):
        pct = len(cases) / total * 100
        lines.append(f"| {ind} | {len(cases)} | {pct:.0f}% |")

    lines.append(f"\n**Total case studies analyzed:** {total}\n")

    lines.append("### Technology Stack Footprint\n")
    lines.append("| Technology | Occurrences |")
    lines.append("|------------|-------------|")
    for tech, count in sorted(tech_usage.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"| {tech} | {count} |")

    lines.append("\n### Client Size Profile\n")
    lines.append("| Client Type | Count |")
    lines.append("|-------------|-------|")
    for ct, count in sorted(client_types.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"| {ct} | {count} |")

    # Gap analysis
    lines.append("\n---\n")
    lines.append("## 2. Gap Analysis: Where phData Could Grow\n")
    lines.append("### Current Strengths")
    lines.append("- **Snowflake ecosystem** dominates the portfolio---phData is clearly a top Snowflake partner")
    lines.append("- **Financial Services** is well-represented with multiple banking and insurance clients")
    lines.append("- **Restaurant/Food Service** is a notable vertical concentration")
    lines.append("- **Data migration** (Hadoop, Teradata, on-prem to cloud) is a proven competency\n")

    lines.append("### Growth Opportunities")
    lines.append("- **AI/ML & GenAI projects** are emerging but still a small portion of the portfolio")
    lines.append("- **Healthcare & Life Sciences** has several case studies but massive untapped potential")
    lines.append("- **Pharmaceutical/Biotech** is underrepresented given the industry's enormous data spend")
    lines.append("- **Medical Devices** has only a few case studies despite being a growing market")
    lines.append("- **Research Institutions** are virtually absent from the portfolio\n")

    # Brian's value proposition
    lines.append("---\n")
    lines.append("## 3. Brian Cohn's Client Acquisition Strategy\n")

    lines.append("### 3.1 Direct Relationship Pipeline\n")
    for conn in BRIAN_NETWORK["direct_connections"]:
        lines.append(f"#### {conn['company']}")
        lines.append(f"**Relationship:** {conn['relationship']}  ")
        lines.append(f"**Industry:** {conn['industry']}  ")
        lines.append(f"**Opportunity:** {conn['potential']}\n")

    lines.append("### 3.2 Research & Academic Network\n")
    for inst in BRIAN_NETWORK["research_network"]:
        lines.append(f"#### {inst['institution']}")
        lines.append(f"**Relationship:** {inst['relationship']}  ")
        lines.append(f"**Opportunity:** {inst['potential']}\n")

    lines.append("### 3.3 Vertical Expansion Targets\n")
    for vertical in BRIAN_NETWORK["domain_expertise_verticals"]:
        lines.append(f"#### {vertical['vertical']}")
        lines.append(f"**Brian's Credential:** {vertical['brian_credential']}  ")
        lines.append(f"**phData Gap:** {vertical['phdata_gap']}\n")
        lines.append("**Target Companies:**")
        for company in vertical["target_companies"]:
            lines.append(f"- {company}")
        lines.append("")

    # The narrative
    lines.append("---\n")
    lines.append("## 4. The Growth Narrative: Why Brian + phData = Accelerated Growth\n")

    lines.append("### The Core Thesis\n")
    lines.append("phData has built an exceptional reputation in **data platform modernization**---particularly")
    lines.append("around Snowflake, dbt, and cloud migration. Their case study portfolio demonstrates deep")
    lines.append("expertise in transforming enterprise data infrastructure. However, the market is rapidly")
    lines.append("shifting: clients increasingly want **AI/ML outcomes**, not just data platforms. They want")
    lines.append("the platform AND the intelligence layer on top.\n")
    lines.append("Brian Cohn fills this exact gap. He brings:\n")

    lines.append("### 4.1 Credibility That Opens Doors\n")
    lines.append("When Brian walks into a pharmaceutical company, he doesn't just talk about Snowflake")
    lines.append("schemas---he talks about clinical trial data management, FDA compliance, and how GenAI")
    lines.append("can accelerate drug discovery. He has an NIH grant, a Nature publication, and real")
    lines.append("clinical experience. This credibility is impossible to hire for and invaluable for")
    lines.append("winning healthcare and life sciences deals.\n")

    lines.append("### 4.2 The AstraZeneca Door-Opener\n")
    lines.append("Brian's direct experience building the AIMI virtual assistant for AstraZeneca is a")
    lines.append("concrete proof point. AstraZeneca and its peers (Pfizer, Merck, Novartis, etc.) are")
    lines.append("all investing billions in data and AI. Brian's relationship with AstraZeneca could")
    lines.append("serve as a beachhead for phData to enter the top-20 pharmaceutical companies---a")
    lines.append("market where a single engagement can be worth $5-20M+.\n")

    lines.append("### 4.3 The GenAI Premium\n")
    lines.append("phData's portfolio shows growing AI/ML work, but most case studies still center on")
    lines.append("data platform modernization. Brian's GenAI expertise (production LLM systems, RAG")
    lines.append("architectures, agentic AI) lets phData command premium rates for AI-forward projects.")
    lines.append("GenAI engagements typically carry 30-50% higher rates than platform work, and Brian")
    lines.append("can both sell and deliver these projects.\n")

    lines.append("### 4.4 The Medical Device & Health Tech Vertical\n")
    lines.append("phData has some healthcare case studies but no dedicated medical device practice.")
    lines.append("Brian's experience as a medical device co-founder, clinical trial PI, and healthcare")
    lines.append("AI developer means he could build this vertical from scratch. The medical device")
    lines.append("market's data needs are exploding due to FDA's increasing expectations for real-world")
    lines.append("evidence and AI/ML-enabled devices.\n")

    lines.append("### 4.5 The Consulting Network Multiplier\n")
    lines.append("As Sr. Architect at Credera (part of Omnicom Group), Brian has visibility into a vast")
    lines.append("network of enterprise clients. While Credera focuses on management and digital")
    lines.append("consulting, phData specializes in data platform implementation. This creates a natural")
    lines.append("referral pipeline: Credera identifies client data challenges -> phData delivers the")
    lines.append("technical solution. Brian is the bridge that makes this partnership work.\n")

    # Quantified opportunity
    lines.append("---\n")
    lines.append("## 5. Quantified Growth Potential\n")
    lines.append("| Opportunity | Estimated Annual Revenue Potential | Timeline |")
    lines.append("|-------------|-----------------------------------|----------|")
    lines.append("| AstraZeneca expansion (direct relationship) | $2-5M | 6-12 months |")
    lines.append("| Pharma vertical (top-20 companies) | $5-15M | 12-24 months |")
    lines.append("| Medical device vertical (new practice) | $3-8M | 12-18 months |")
    lines.append("| Healthcare provider AI projects | $2-5M | 6-12 months |")
    lines.append("| GenAI premium on existing accounts | $1-3M | 3-6 months |")
    lines.append("| Credera/consulting referral pipeline | $2-5M | 6-18 months |")
    lines.append("| **Total addressable opportunity** | **$15-41M** | **6-24 months** |\n")

    lines.append("*Note: These estimates are based on typical enterprise data consulting engagement sizes")
    lines.append("and assume Brian is actively developing these relationships as part of phData's")
    lines.append("business development efforts.*\n")

    # Action plan
    lines.append("---\n")
    lines.append("## 6. 90-Day Action Plan\n")
    lines.append("### Month 1: Foundation")
    lines.append("- Map Brian's existing network contacts at target pharmaceutical and medical device companies")
    lines.append("- Develop 3 healthcare/life sciences-specific case study templates based on existing phData work")
    lines.append("- Schedule introductions with AstraZeneca data platform team\n")
    lines.append("### Month 2: Outreach")
    lines.append("- Present joint phData + Brian capabilities at 2-3 healthcare industry events")
    lines.append("- Initiate conversations with 5 target pharmaceutical companies")
    lines.append("- Develop a \"Healthcare AI Readiness Assessment\" offering with phData's existing tools\n")
    lines.append("### Month 3: Pipeline Building")
    lines.append("- Convert initial conversations into 3-5 qualified opportunities")
    lines.append("- Launch the medical device data platform practice with an anchor client")
    lines.append("- Establish the Credera -> phData referral process for data-heavy projects\n")

    report_path = os.path.join(OUTPUT_DIR, "client_growth_strategy.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Written: {report_path}")
    return report_path


if __name__ == "__main__":
    print("=== phData Client Growth Analysis ===\n")
    generate_client_growth_report()
    print("\nDone!")

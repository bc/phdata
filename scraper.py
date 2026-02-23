#!/usr/bin/env python3
"""phData Case Study Scraper - Scrapes all case studies and stores in SQLite with BM25 search."""

import requests
import sqlite3
import json
import time
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phdata_cases.db")

CASE_STUDY_URLS = [
    "https://www.phdata.io/case-studies/improved-tableau-performance-during-data-migration-at-restaurant-chain/",
    "https://www.phdata.io/case-studies/global-energy-leader-modernizes-analytics-by-migrating-500-iot-tables-60-synapse-pipelines-to-snowflake-with-dbt/",
    "https://www.phdata.io/case-studies/ai-data-strategy-for-a-national-procurement-platform/",
    "https://www.phdata.io/case-studies/edtech-firm-saves-millions-in-course-curriculum-creation-using-knowledge-graphs-and-ai/",
    "https://www.phdata.io/case-studies/chemical-conglomerate-transforms-sap-data-in-snowflake-for-analytic-insights/",
    "https://www.phdata.io/case-studies/data-strategy-identifies-up-to-30m-revenue-uplift-and-over-250k-annual-savings-for-financial-services-leader/",
    "https://www.phdata.io/case-studies/financial-services-firm-enhances-contract-inquiry-efficiency-and-insights-with-aws/",
    "https://www.phdata.io/case-studies/large-lawncare-company-moves-sap-data-to-snowflake/",
    "https://www.phdata.io/case-studies/acclaimed-mortgage-origination-and-servicing-company-modernizes-data-stack/",
    "https://www.phdata.io/case-studies/order-co-accelerates-automation-with-agentic-ai-on-aws/",
    "https://www.phdata.io/case-studies/ai-marketing-leader-cuts-onboarding-from-months-to-days-with-snowflake-native-app/",
    "https://www.phdata.io/case-studies/investment-firm-establishes-scalable-data-governance-with-microsoft-fabric-purview-and-phdata/",
    "https://www.phdata.io/case-studies/innovative-regional-bank-translates-its-transformation-layer-to-snowflake/",
    "https://www.phdata.io/case-studies/data-driven-pharmaceutical-giant-transforms-veeva-qms-data-for-power-bi-analytics-with-snowflake/",
    "https://www.phdata.io/case-studies/biotech-leader-transforms-and-scales-analytics-platform-on-aws/",
    "https://www.phdata.io/case-studies/restaurant-chain-massively-scales-data-platform-on-aws/",
    "https://www.phdata.io/case-studies/alteryx-workflows-and-power-automate-save-thousands-of-hours-in-a-global-restaurant-chain/",
    "https://www.phdata.io/case-studies/phdata-helps-leading-music-retailer-migrate-83-tableau-dashboards-to-omni-in-11-weeks/",
    "https://www.phdata.io/case-studies/fortune-500-construction-engineering-giant-migrates-to-snowflake-for-improved-flexibility-scalability/",
    "https://www.phdata.io/case-studies/fortune-500-biotech-and-pharma-company-optimizes-its-demand-planning-process-using-snowflake/",
    "https://www.phdata.io/case-studies/leading-speciality-insurance-provider-migrates-data-stack-to-the-cloud/",
    "https://www.phdata.io/case-studies/global-restaurant-chain-uses-alteryx-snowflake-to-get-insights-on-its-powerbi-environment/",
    "https://www.phdata.io/case-studies/giant-real-estate-firm-utilizes-snowflake-for-rapid-data-center-replication/",
    "https://www.phdata.io/case-studies/top-jeweler-replicates-sap-data-to-snowflake/",
    "https://www.phdata.io/case-studies/fast-growing-dental-admin-support-organization-implements-data-processing-with-snowflake-to-improve-revenue-capture/",
    "https://www.phdata.io/case-studies/construction-powerhouse-leans-on-snowflake-to-enable-data-driven-business-decisions/",
    "https://www.phdata.io/case-studies/leading-learning-platform-utilizes-ai-applications-to-improve-learner-experience/",
    "https://www.phdata.io/case-studies/restaurant-chain-streamlines-it-resolution-across-thousands-of-locations-using-generative-ai/",
    "https://www.phdata.io/case-studies/fsi-giant-uses-rag-ai-chatbot-for-contract-inquiries/",
    "https://www.phdata.io/case-studies/global-asset-management-firm-optimizes-performance-reduces-cost-by-migrating-to-snowflake/",
    "https://www.phdata.io/case-studies/successful-us-financial-and-tax-consulting-enterprise-begins-data-modernization-journey-with-snowflake-phdata/",
    "https://www.phdata.io/case-studies/global-software-company-centralizes-refreshes-data-from-ma-in-snowflake/",
    "https://www.phdata.io/case-studies/supply-chain-software-leader-uncovers-snowflake-cost-savings-optimizations/",
    "https://www.phdata.io/case-studies/global-restaurant-chain-uses-alteryx-and-ui-path-for-new-hire-documentation-review/",
    "https://www.phdata.io/case-studies/us-telecom-giant-sharpens-ml-capabilities-using-feature-store-snowflake/",
    "https://www.phdata.io/case-studies/north-american-cpg-retail-giant-centralizes-business-unit-data-to-analyze-direct-spending/",
    "https://www.phdata.io/case-studies/prominent-investment-bank-launches-data-warehouse-as-a-service-on-snowflake/",
    "https://www.phdata.io/case-studies/top-regional-bank-modernizes-its-data-warehouse-with-snowflake/",
    "https://www.phdata.io/case-studies/streamlining-demand-forecasting-farm-supplier-modernizes-an-excel-headache-with-dataiku-snowflake/",
    "https://www.phdata.io/using-alteryx-for-sustainability-reporting-on-a-global-restaurant-chain/",
    "https://www.phdata.io/case-studies/top-north-american-grocery-company-leans-on-phdata-for-snowflake-cost-saving-optimizations/",
    "https://www.phdata.io/case-studies/high-profile-digital-advertising-firm-leverages-snowpark-to-slash-data-runtimes-compute-costs/",
    "https://www.phdata.io/case-studies/major-telecom-provider-enhances-efficiency-with-automated-reporting-suite/",
    "https://www.phdata.io/case-studies/renowned-global-developer-of-automation-testing-measurement-systems-migrates-to-snowflake-from-exadata-and-qubole/",
    "https://www.phdata.io/case-studies/fortune-500-cpg-company-saves-200-hours-annually-with-automated-dashboards/",
    "https://www.phdata.io/case-studies/premier-global-title-services-company-migrates-to-snowflake-to-streamline-operations-optimize-growth/",
    "https://www.phdata.io/case-studies/established-financial-company-improves-latency-by-90-by-migrating-its-etl-processing-to-snowflake/",
    "https://www.phdata.io/case-studies/innovative-electronics-manufacturing-company-partners-with-phdata-to-adopt-sigma-computing-for-bi-reporting/",
    "https://www.phdata.io/case-studies/esteemed-healthcare-provider-uses-sentiment-analysis-to-improve-media-monitoring/",
    "https://www.phdata.io/case-studies/bank-boost-analytics-saves-70k-with-alteryx-and-phdata/",
    "https://www.phdata.io/case-studies/cancer-research-organization-leverages-snowflake-and-sigma-to-build-data-reporting-system/",
    "https://www.phdata.io/case-studies/saas-provider-uses-dbt-to-standardize-metrics-and-centralize-kpis/",
    "https://www.phdata.io/case-studies/engineering-company-migrates-from-teradata-to-snowflake/",
    "https://www.phdata.io/case-studies/automotive-lender-enhances-analytics-with-snowflake-migration/",
    "https://www.phdata.io/case-studies/prominent-professional-services-company-migrates-from-hadoop-to-snowflake/",
    "https://www.phdata.io/case-studies/trucking-company-simplifies-on-prem-data-migration-to-snowflake/",
    "https://www.phdata.io/case-studies/medical-company-uses-ml-to-accelerate-advances-in-sleep-apnea-technology/",
    "https://www.phdata.io/case-studies/snowpark-and-ml-assist-healthcare-technology-company-in-predicting-organizational-revenue-cycles/",
    "https://www.phdata.io/case-studies/finance-firm-utilizes-machine-learning-to-detect-financial-anomalies/",
    "https://www.phdata.io/case-studies/major-regional-bank-automates-reports-of-commercial-lending/",
    "https://www.phdata.io/case-studies/global-manufacturing-company-swiftly-migrates-to-snowflake-with-no-interruptions/",
    "https://www.phdata.io/case-studies/financial-services-company-utilizes-machine-learning-to-predict-customer-potential/",
    "https://www.phdata.io/case-studies/global-talent-company-roadmaps-the-merging-of-data-through-a-modernized-technology-stack/",
    "https://www.phdata.io/case-studies/marketing-company-migrates-hadoop-to-snowflake-with-snowpark/",
    "https://www.phdata.io/case-studies/cpg-company-creates-powerful-forecasts-for-new-product-launch/",
    "https://www.phdata.io/case-studies/cpg-company-migrates-to-tableau-cloud-to-server/",
    "https://www.phdata.io/case-studies/municipal-company-utilizes-snowflake-power-bi-to-gain-insights-into-energy-usage/",
    "https://www.phdata.io/case-studies/cpg-enterprise-successfully-implements-power-bi-premium/",
    "https://www.phdata.io/case-studies/b2b-software-company-modernizes-data-stack-with-snowflake-airflow-dbt/",
    "https://www.phdata.io/case-studies/medical-device-maker-streamlines-its-snowflake-data-ecosystem/",
    "https://www.phdata.io/case-studies/fast-food-chain-explores-new-machine-learning-capabilities/",
    "https://www.phdata.io/case-studies/crm-company-partners-with-phdata-for-contact-data/",
    "https://www.phdata.io/case-studies/legal-services-provider-transforms-staffing-process-with-xgboost-prophet/",
    "https://www.phdata.io/case-studies/life-insurance-company-successfully-migrates-from-cloudera-to-aws/",
    "https://www.phdata.io/case-studies/nextgen-healthcare/",
    "https://www.phdata.io/case-studies/healthcare-marketplace-meets-compliance-requirements-by-automating/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS case_studies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        client TEXT,
        industry TEXT,
        challenge TEXT,
        solution TEXT,
        results TEXT,
        technologies TEXT,
        full_text TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS google_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        url TEXT,
        title TEXT,
        snippet TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS case_studies_fts
        USING fts5(title, client, industry, challenge, solution, results, technologies, full_text, content=case_studies, content_rowid=id)""")
    conn.commit()
    return conn


def scrape_case_study(url):
    """Scrape a single case study page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Extract title
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Extract all text content from the main article area
        # Try common content selectors
        content_area = None
        for selector in ["article", ".entry-content", ".post-content", ".case-study-content", "main", ".content"]:
            content_area = soup.select_one(selector)
            if content_area:
                break

        if not content_area:
            content_area = soup.find("body")

        full_text = content_area.get_text(separator="\n", strip=True) if content_area else ""

        # Try to extract structured sections
        sections = {"challenge": "", "solution": "", "results": ""}
        all_headings = soup.find_all(["h2", "h3", "h4"])
        for h in all_headings:
            heading_text = h.get_text(strip=True).lower()
            section_content = []
            sibling = h.find_next_sibling()
            while sibling and sibling.name not in ["h2", "h3", "h4"]:
                text = sibling.get_text(strip=True)
                if text:
                    section_content.append(text)
                sibling = sibling.find_next_sibling()
            content = "\n".join(section_content)

            if any(k in heading_text for k in ["challenge", "problem", "situation", "background"]):
                sections["challenge"] += content + "\n"
            elif any(k in heading_text for k in ["solution", "approach", "what we did", "how"]):
                sections["solution"] += content + "\n"
            elif any(k in heading_text for k in ["result", "outcome", "impact", "benefit"]):
                sections["results"] += content + "\n"

        # Extract technologies/tools mentioned
        tech_keywords = [
            "Snowflake", "dbt", "Airflow", "AWS", "Azure", "Databricks", "Tableau",
            "Power BI", "Sigma", "Alteryx", "Dataiku", "Python", "Spark", "Kafka",
            "Terraform", "Kubernetes", "Docker", "Fivetran", "Matillion", "Informatica",
            "SAP", "Hadoop", "Teradata", "Cloudera", "Redshift", "BigQuery", "Looker",
            "Omni", "Snowpark", "ML", "Machine Learning", "AI", "GenAI", "RAG",
            "NLP", "XGBoost", "Prophet", "Feature Store", "UiPath", "Microsoft Fabric",
            "Purview", "Veeva", "FastAPI", "Django", "React", "S3", "EC2", "Lambda",
            "Bedrock", "SageMaker", "OpenAI", "LLM", "GPT", "Claude"
        ]
        found_tech = []
        for tech in tech_keywords:
            if re.search(r'\b' + re.escape(tech) + r'\b', full_text, re.IGNORECASE):
                found_tech.append(tech)

        # Extract client/industry hints from meta or content
        client = ""
        industry = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            client = meta_desc.get("content", "")[:200]

        # Try to detect industry from URL and content
        industry_map = {
            "restaurant": "Restaurant & Food Service",
            "bank": "Financial Services",
            "financial": "Financial Services",
            "insurance": "Insurance",
            "healthcare": "Healthcare",
            "medical": "Healthcare",
            "pharma": "Pharmaceutical",
            "biotech": "Biotechnology",
            "cpg": "Consumer Packaged Goods",
            "retail": "Retail",
            "telecom": "Telecommunications",
            "energy": "Energy",
            "manufacturing": "Manufacturing",
            "construction": "Construction",
            "real-estate": "Real Estate",
            "dental": "Healthcare",
            "cancer": "Healthcare",
            "edtech": "Education Technology",
            "learning": "Education",
            "legal": "Legal Services",
            "marketing": "Marketing",
            "software": "Technology",
            "saas": "Technology",
            "automotive": "Automotive",
            "trucking": "Transportation",
            "grocery": "Retail",
            "talent": "Human Resources",
            "mortgage": "Financial Services",
            "lawncare": "Services",
        }
        url_lower = url.lower()
        for key, val in industry_map.items():
            if key in url_lower or key in full_text.lower()[:500]:
                industry = val
                break

        return {
            "url": url,
            "title": title,
            "client": client,
            "industry": industry,
            "challenge": sections["challenge"].strip(),
            "solution": sections["solution"].strip(),
            "results": sections["results"].strip(),
            "technologies": ", ".join(found_tech),
            "full_text": full_text[:10000],
        }
    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        return None


def scrape_all_case_studies(conn):
    """Scrape all case studies and insert into DB."""
    c = conn.cursor()
    total = len(CASE_STUDY_URLS)
    for i, url in enumerate(CASE_STUDY_URLS):
        # Check if already scraped
        c.execute("SELECT id FROM case_studies WHERE url = ?", (url,))
        if c.fetchone():
            print(f"  [{i+1}/{total}] Already scraped: {url.split('/')[-2]}")
            continue

        print(f"  [{i+1}/{total}] Scraping: {url.split('/')[-2]}")
        data = scrape_case_study(url)
        if data:
            c.execute("""INSERT OR REPLACE INTO case_studies
                (url, title, client, industry, challenge, solution, results, technologies, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (data["url"], data["title"], data["client"], data["industry"],
                 data["challenge"], data["solution"], data["results"],
                 data["technologies"], data["full_text"]))
            conn.commit()
        time.sleep(0.5)  # Be polite

    # Rebuild FTS index
    c.execute("DELETE FROM case_studies_fts")
    c.execute("""INSERT INTO case_studies_fts(rowid, title, client, industry, challenge, solution, results, technologies, full_text)
        SELECT id, title, client, industry, challenge, solution, results, technologies, full_text FROM case_studies""")
    conn.commit()
    print(f"\nDone! Scraped {total} case studies.")


def google_site_search(conn, query, num_results=10):
    """Search Google for site:phdata.io results and store them."""
    search_query = f"site:phdata.io {query}"
    encoded = quote_plus(search_query)
    url = f"https://www.google.com/search?q={encoded}&num={num_results}"

    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        results = []
        for g in soup.select("div.g, div[data-sokoban-container]"):
            link_tag = g.find("a", href=True)
            title_tag = g.find("h3")
            snippet_tag = g.select_one(".VwiC3b, .IsZvec, .s3v9rd")

            if link_tag and title_tag:
                result = {
                    "query": query,
                    "url": link_tag["href"],
                    "title": title_tag.get_text(strip=True),
                    "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                }
                results.append(result)

                c = conn.cursor()
                c.execute("""INSERT INTO google_results (query, url, title, snippet)
                    VALUES (?, ?, ?, ?)""",
                    (result["query"], result["url"], result["title"], result["snippet"]))

        conn.commit()
        return results
    except Exception as e:
        print(f"  Google search error: {e}")
        return []


if __name__ == "__main__":
    print("=== phData Case Study Scraper ===\n")
    conn = init_db()

    print("Phase 1: Scraping all case studies...")
    scrape_all_case_studies(conn)

    print("\nPhase 2: Google site search for additional context...")
    search_queries = [
        "machine learning AI case study",
        "generative AI LLM",
        "data modernization snowflake",
        "healthcare analytics",
        "predictive analytics ML",
        "RAG chatbot AI agent",
        "data strategy consulting",
        "cloud migration AWS Azure",
    ]
    for q in search_queries:
        print(f"  Searching: {q}")
        google_site_search(conn, q)
        time.sleep(1)

    # Summary
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM case_studies")
    count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM google_results")
    gcount = c.fetchone()[0]
    print(f"\nDatabase: {count} case studies, {gcount} Google results")
    print(f"Database saved to: {DB_PATH}")
    conn.close()

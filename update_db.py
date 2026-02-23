#!/usr/bin/env python3
"""Update the database with detailed case study content from WebFetch results."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phdata_cases.db")

# Detailed case study data from web scraping
DETAILED_CASES = [
    {
        "url": "https://www.phdata.io/case-studies/order-co-accelerates-automation-with-agentic-ai-on-aws/",
        "client": "Order.co - B2B procurement technology company (160 employees), managing demand approaching $1B in annual purchasing volume. Clients include Hugo Boss, Miniso, Lark Hotels.",
        "industry": "Technology",
        "challenge": "Manual browser-based ordering workflows with traditional RPA requiring heavy maintenance. Escalating labor costs, frequent errors, slow transaction cycles, and shifting UIs/CAPTCHAs defeating conventional automation.",
        "solution": "Agentic AI automation framework delivered in 6 weeks. Amazon Nova-Act as the intelligent brain generating actions to navigate vendor platforms. Golden Paths (documented successful strategies) stored as Vendor Agent Plans. Action Validation module reviews every LLM instruction before execution. Nightly reviews refine agent strategies. Containerized in ECS Pods for scalability.",
        "results": "100% success rate across all 7 pilot vendors; multi-hour processes compressed to minutes; streamlined vendor onboarding; complete auditability; scalable without proportional headcount increases.",
        "technologies": "Amazon Nova-Act, Anthropic Claude Sonnet, Amazon Bedrock, PlaywrightMCP, Stagehand, Playwright, AWS ECS, Agentic AI",
    },
    {
        "url": "https://www.phdata.io/case-studies/fsi-giant-uses-rag-ai-chatbot-for-contract-inquiries/",
        "client": "Diversified financial services company providing life insurance, retirement plans, investment services, and wealth management to millions of US customers.",
        "industry": "Financial Services",
        "challenge": "Manual contract inquiry process averaging 3 days per response. Multiple email exchanges, manual contract location, frequent missed details. Inquiry volume growing 40% annually.",
        "solution": "Custom RAG chatbot with vector database on AWS. Three components: contract RAG ingestion pipeline, vector database, and chatbot interface.",
        "results": "Response time reduced from 3 days to same-day (70%+ reduction); retrieval in under 5 seconds; reduced 5 FTEs to part-time oversight; ~$400,000 annual labor cost savings; handles 40% yearly inquiry growth.",
        "technologies": "AWS Lambda, Amazon Textract, LangChain, Amazon Titan LLM, Lance DB, AWS S3, Claude Sonnet 3.5, Amazon Bedrock, Streamlit, Docker, Kubernetes, RAG",
    },
    {
        "url": "https://www.phdata.io/case-studies/restaurant-chain-streamlines-it-resolution-across-thousands-of-locations-using-generative-ai/",
        "client": "Leading American fast-food chain with over 2,700 restaurants, headquartered in the Southeast, adding ~185 locations annually.",
        "industry": "Restaurant & Food Service",
        "challenge": "Escalating IT support demands with network expansion. Options were either expand IT department significantly or accept operational delays. Labor-intensive phone/email-based support.",
        "solution": "Conversational NLP interface powered by RAG. Ingests ServiceNow IT documentation, converts to vector embeddings, generates responses using LLM to prevent hallucinations.",
        "results": "10,000+ IT documents vector-encoded; 30x faster resolution for common IT questions; IT teams redirected to complex issues; expanded to additional bots.",
        "technologies": "AWS Lambda, Amazon Bedrock, API Gateway, Vector Database, Mistral Large, ServiceNow, Generative AI, RAG, NLP",
    },
    {
        "url": "https://www.phdata.io/case-studies/edtech-firm-saves-millions-in-course-curriculum-creation-using-knowledge-graphs-and-ai/",
        "client": "Leading online education provider specializing in digital learning materials and curriculum development at scale.",
        "industry": "Education Technology",
        "challenge": "Course creation costing $80K-$150K per course (tens of millions annually). Manual compliance with state-specific standards. Slow, resource-intensive process limiting market expansion.",
        "solution": "Course in a Day initiative. Workflow mapping and optimization, system integration, automated compliance via knowledge graph on Amazon Neptune, AI platform on serverless AWS with Snowflake and dbt.",
        "results": "Course creation cost dropped from $120K to $15K (80% reduction); ~$1M year-one OPEX savings; ~$10M projected annual savings; faster distribution across states; improved compliance.",
        "technologies": "Amazon Neptune, AWS, Snowflake, dbt, GenAI, Knowledge Graphs, AI",
    },
    {
        "url": "https://www.phdata.io/case-studies/medical-company-uses-ml-to-accelerate-advances-in-sleep-apnea-technology/",
        "client": "Medical device manufacturer advancing therapeutic technology for sleep apnea.",
        "industry": "Healthcare",
        "challenge": "Needed to improve algorithm for airway stimulation during sleep apnea events. Questioned whether ML/AI could enhance existing algorithm but lacked internal ML resources.",
        "solution": "Built MLOps platform within Azure ML over 13-week engagement. Tested multiple modeling approaches (LSTM, CNN, FCN, XGBoost, TapNet) to forecast inhalation patterns.",
        "results": "Established repeatable MLOps process; models demonstrated potential improvement when combining existing approach with ML methods.",
        "technologies": "Azure Machine Learning, LSTM, CNN, FCN, XGBoost, TapNet, Machine Learning, MLOps",
    },
    {
        "url": "https://www.phdata.io/case-studies/snowpark-and-ml-assist-healthcare-technology-company-in-predicting-organizational-revenue-cycles/",
        "client": "Healthcare technology platform company specializing in predicting customer revenue cycles.",
        "industry": "Healthcare",
        "challenge": "Daily data transformations requiring 20+ hours. Data extracted from Snowflake, processed externally, then reloaded. Failed jobs couldn't recover before next business day.",
        "solution": "Migrated Flask data models to Pandas Series compatible with Snowpark. Used JSON for flexible output. Integrated cachetools for optimization. Eliminated external data transfers by keeping transformations in Snowflake.",
        "results": "Runtime reduced from 20 hours to 13 minutes; 20x cost reduction; eliminated external data transfers; enhanced predictive model performance.",
        "technologies": "Snowflake, Snowpark, Python, Machine Learning, Pandas",
    },
    {
        "url": "https://www.phdata.io/case-studies/finance-firm-utilizes-machine-learning-to-detect-financial-anomalies/",
        "client": "Global finance firm specializing in disputes/investigations, corporate finance, and performance improvement advisory.",
        "industry": "Financial Services",
        "challenge": "Needed to detect suspicious behavior in market trading data for large-scale investigation. Small number of known anomalies relative to massive data volume.",
        "solution": "Anomaly detection model using Azure ML with MLFlow for experiment tracking. Modified known approaches for novel problem.",
        "results": "Accurate anomaly detection model covering 10+ markets across nearly a decade of data. Enabled identification of suspicious activities.",
        "technologies": "Azure ML, MLFlow, Machine Learning, Anomaly Detection",
    },
    {
        "url": "https://www.phdata.io/case-studies/us-telecom-giant-sharpens-ml-capabilities-using-feature-store-snowflake/",
        "client": "Prominent US telecom industry leader.",
        "industry": "Telecommunications",
        "challenge": "Fragmented data processes with multiple ad hoc ML data capturing methods. Code duplication, human errors during model updates, inconsistent data manipulation standards.",
        "solution": "Feature Store built on Feast Framework integrated with Snowflake. Centralized data management, standardized access, governance layer, structured development workflow. CI/CD via GitHub Actions.",
        "results": "Improved data standards; consolidated datasets; enhanced ML engineer collaboration; reduced code duplication and errors. Delivered in 8 weeks.",
        "technologies": "Feast Framework, Snowflake, GitHub Actions, Feature Store, Machine Learning",
    },
    {
        "url": "https://www.phdata.io/case-studies/esteemed-healthcare-provider-uses-sentiment-analysis-to-improve-media-monitoring/",
        "client": "Major US healthcare provider and Fortune 500 company.",
        "industry": "Healthcare",
        "challenge": "Manual review of thousands of newspaper articles lacked consistency. Different employees graded the same articles differently. Needed standardized, objective scoring for brand sentiment.",
        "solution": "Alteryx workflow with custom R code performing sentiment analysis at overall and sentence levels. Random forest model to standardize and improve results.",
        "results": "Thousands of articles rated in under 15 minutes with consistent, objective scoring. Developed in under 8 weeks.",
        "technologies": "Alteryx, R, Random Forest, Sentiment Analysis, NLP, Machine Learning",
    },
    {
        "url": "https://www.phdata.io/case-studies/leading-learning-platform-utilizes-ai-applications-to-improve-learner-experience/",
        "client": "EdTech firm specializing in personalized learning (K-12 online education and career learning programs).",
        "industry": "Education Technology",
        "challenge": "Lacked foundational AI infrastructure and clear strategy. Initial AI implementation perceived as impersonal. Data quality/governance issues. A GenAI POC hallucinated in front of leadership.",
        "solution": "Modular platform for AI assistants (digital tutors and graders). Orchestration system with feature store, external Omnisearch for curriculum, real-time session management.",
        "results": "5x faster time-to-value for future AI chat applications; improved personalization; AI Foundation Platform established.",
        "technologies": "AWS API Gateway, AWS Lambda, AWS Lex V2, Amazon Bedrock, Claude Sonnet 3.5, AWS ElastiCache, GenAI, LLM, AI",
    },
    {
        "url": "https://www.phdata.io/case-studies/ai-data-strategy-for-a-national-procurement-platform/",
        "client": "Leading procurement solutions organization serving enterprise and public-sector members.",
        "industry": "Technology",
        "challenge": "Outgrown data foundation; inconsistent KPIs; manual report stitching; legal/compliance lacked centralized contract visibility; master-data inconsistencies.",
        "solution": "Three-phase engagement: Assessment, Design (Medallion Architecture on Snowflake with AI/ML patterns for document intelligence), Mobilization (24-month roadmap).",
        "results": "$7.5M-$12M annual revenue potential; $3.6M-$10M preventable churn; $0.5M-$1.5M campaign optimization lift; $9.2M-$16.2M spend normalization upside.",
        "technologies": "Snowflake, Coalesce, Azure ML, Document AI, Machine Learning, AI",
    },
    {
        "url": "https://www.phdata.io/case-studies/ai-marketing-leader-cuts-onboarding-from-months-to-days-with-snowflake-native-app/",
        "client": "AI-powered marketing technology company focused on mobile marketing solutions.",
        "industry": "Technology",
        "challenge": "Client onboarding required slow, manual Snowflake data share setup. Complex, error-prone workflow delaying time-to-value by weeks or months.",
        "solution": "Custom Snowflake Native App automating data sharing with user-friendly wizard, automated private listing creation, real-time monitoring, enterprise-grade security.",
        "results": "Onboarding reduced from months to days; 100+ customers automating data sharing without code; Marketplace launch within 16 weeks.",
        "technologies": "Snowflake Native App, Snowflake Marketplace, Snowflake API",
    },
    {
        "url": "https://www.phdata.io/case-studies/financial-services-firm-enhances-contract-inquiry-efficiency-and-insights-with-aws/",
        "client": "Diversified financial services organization (life insurance, retirement, investments, wealth management) serving millions of US customers.",
        "industry": "Financial Services",
        "challenge": "Manual contract inquiry process with 3-day average response time. Multiple email exchanges, frequent errors/omissions. 40% annual inquiry volume growth.",
        "solution": "Data lake architecture (S3, Glue, Redshift Spectrum); Amazon Kendra for natural language contract search; AWS Step Functions for workflow automation. Migrated from Hadoop to AWS.",
        "results": "70% response time reduction; same-day responses standard; improved accuracy; reduced email exchanges.",
        "technologies": "Amazon S3, AWS Glue, Amazon Redshift, Amazon Kendra, AWS Step Functions, Tableau, RStudio, AWS",
    },
    {
        "url": "https://www.phdata.io/case-studies/legal-services-provider-transforms-staffing-process-with-xgboost-prophet/",
        "client": "On-demand legal services company serving nearly 50% of Fortune 100 companies.",
        "industry": "Legal Services",
        "challenge": "Losing up to 25% of potential deals due to staffing shortages. Unable to accurately predict demand or available talent supply. Lacked internal ML skillset.",
        "solution": "Demand forecasting using Salesforce pipeline data with XGBoost and Facebook Prophet. Supply forecasting via rules-based methodology. Delivered in 5 weeks.",
        "results": "Two predictive models delivering 12-week forecasts at ~80% accuracy. Transformed staffing from reactive to proactive.",
        "technologies": "AWS SageMaker, Power BI, XGBoost, Prophet, Salesforce, Machine Learning",
    },
    {
        "url": "https://www.phdata.io/case-studies/fast-food-chain-explores-new-machine-learning-capabilities/",
        "client": "Fast-growing US fast food establishment.",
        "industry": "Restaurant & Food Service",
        "challenge": "Needed to assess whether Amazon Redshift ML would benefit existing ML operations. Had multiple algorithms running.",
        "solution": "POC recreating existing algorithm within Amazon Redshift ML. Discovered BYOM limited to inference only, pivoted to rebuilding AAR model.",
        "results": "Exposed strengths and limitations of Redshift ML; identified appropriate use cases; provided reproduction code.",
        "technologies": "Amazon Redshift ML, AWS Glue, CatBoost, Machine Learning",
    },
    {
        "url": "https://www.phdata.io/case-studies/cancer-research-organization-leverages-snowflake-and-sigma-to-build-data-reporting-system/",
        "client": "Renowned cancer treatment and research organization serving researchers, investigators, grant-writers, and medical personnel.",
        "industry": "Healthcare",
        "challenge": "Staff waited extended periods for data reports; standard reports took 20+ minutes. Non-technical users couldn't generate reports independently.",
        "solution": "Layered Sigma Computing on existing Snowflake infrastructure for no-code, cloud-based reporting with longitudinal filtering.",
        "results": "Report generation from 20+ minutes to under 1 minute; 2,500 variables across 500,000+ patient records; self-serve access eliminated bottleneck.",
        "technologies": "Snowflake, Sigma Computing",
    },
    {
        "url": "https://www.phdata.io/case-studies/nextgen-healthcare/",
        "client": "NextGen Healthcare - integrated healthcare technology and services platform operating the NextGen Health Data Hub.",
        "industry": "Healthcare",
        "challenge": "Health data locked in hard-to-consume JSON objects. Limited analytics capability. Scalability concerns. Lacked internal Snowflake expertise.",
        "solution": "Automated Snowflake provisioning; streamed JSON into Snowflake in near real-time; automated ingestion of 60+ tables from S3; custom dbt code generation; governance framework; built NextGen Health Data Hub Insights product.",
        "results": "12 weeks from concept to production; transformed inaccessible JSON to curated tabular models; near real-time data streaming.",
        "technologies": "Snowflake, AWS S3, dbt",
    },
    {
        "url": "https://www.phdata.io/case-studies/healthcare-marketplace-meets-compliance-requirements-by-automating/",
        "client": "Major online marketplace connecting patients with healthcare providers using advanced analytics.",
        "industry": "Healthcare",
        "challenge": "Needed consistent backup and recovery for Snowflake and AWS. Required automated resource configuration by customer tier. Healthcare certification requirements.",
        "solution": "Automated data pushes for backup; refactored Terraform repos; CI/CD pipeline; applied three-tier pricing model.",
        "results": "Sustainable backup/recovery ahead of schedule and under budget; compliance requirements met.",
        "technologies": "Snowflake, AWS, S3, Kafka, Kinesis, Lambda, Terraform, Flyway",
    },
    {
        "url": "https://www.phdata.io/case-studies/biotech-leader-transforms-and-scales-analytics-platform-on-aws/",
        "client": "Global biotechnology leader advancing breakthrough therapies.",
        "industry": "Biotechnology",
        "challenge": "Outdated analytics platforms. Fragmented reporting and manual data integration. Scalability constraints. Data silos creating compliance burdens.",
        "solution": "Migrated 153 legacy OBIEE reports to Power BI with Snowflake. Orchestrated hundreds of pipelines using Astronomer. Integrated Fivetran and dbt. 24x7 incident response.",
        "results": "Supports 2,000+ users; 20M+ queries/month across 7 business units; <2 min average ticket response; 3,500+ service requests/year.",
        "technologies": "AWS, Snowflake, Power BI, Astronomer, Apache Airflow, Fivetran, dbt",
    },
    {
        "url": "https://www.phdata.io/case-studies/data-driven-pharmaceutical-giant-transforms-veeva-qms-data-for-power-bi-analytics-with-snowflake/",
        "client": "One of the world's leading pharmaceutical companies.",
        "industry": "Pharmaceutical",
        "challenge": "Limited reporting flexibility in Veeva QMS; inconsistent governance; slow report generation with heavy IT reliance.",
        "solution": "Informatica for Veeva QMS ingestion into Snowflake; dbt for standardized models; Snowflake RBAC and row-level security; Airflow for automated refreshes; Power BI dashboards.",
        "results": "Enhanced quality workflows; reduced audit times; business users explore data independently; scalable processes.",
        "technologies": "Snowflake, dbt, Apache Airflow, Informatica, Power BI, Veeva",
    },
]


def update_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    updated = 0
    for case in DETAILED_CASES:
        url = case["url"]
        full_text = f"{case.get('client', '')} {case.get('challenge', '')} {case.get('solution', '')} {case.get('results', '')}"

        c.execute("""UPDATE case_studies SET
            client = ?,
            industry = ?,
            challenge = ?,
            solution = ?,
            results = ?,
            technologies = ?,
            full_text = ?
            WHERE url = ?""",
            (case.get("client", ""), case.get("industry", ""),
             case.get("challenge", ""), case.get("solution", ""),
             case.get("results", ""), case.get("technologies", ""),
             full_text, url))
        if c.rowcount > 0:
            updated += 1

    conn.commit()

    # Rebuild FTS
    c.execute("DROP TABLE IF EXISTS case_studies_fts")
    c.execute("""CREATE VIRTUAL TABLE case_studies_fts
        USING fts5(title, client, industry, challenge, solution, results, technologies, full_text)""")
    c.execute("SELECT title, client, industry, challenge, solution, results, technologies, full_text FROM case_studies")
    for row in c.fetchall():
        c.execute("INSERT INTO case_studies_fts VALUES (?,?,?,?,?,?,?,?)", row)
    conn.commit()
    conn.close()

    print(f"Updated {updated} case studies with detailed content")
    print("FTS5 index rebuilt")


if __name__ == "__main__":
    update_database()

#!/usr/bin/env python3
"""Analyze phData case studies against Brian Cohn's profile to find best matches."""

import sqlite3
import os
import json
from search_engine import PhDataSearchEngine, tokenize
from rank_bm25 import BM25Okapi

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phdata_cases.db")
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Brian Cohn's profile - synthesized from briancohn.com and public sources
BRIAN_PROFILE = {
    "name": "Brian Cohn, Ph.D.",
    "current_role": "Senior Architect at Credera (GenAI and Advanced Research), Chief Scientist at Kaspect, Co-Founder of Adventure Biofeedback",
    "education": "Ph.D. in Computer Science, USC Viterbi School of Engineering",
    "core_expertise": [
        "Machine learning and generative AI",
        "Computational neuroscience and biomechanics",
        "Healthcare technology and medical devices",
        "Product development and commercialization",
        "Human-in-the-loop architecture design",
        "AWS pipeline architecture (FastAPI, Django, cloud infrastructure)",
        "Clinical trial design and execution (NIH SBIR PI)",
        "Signal processing and closed-loop DSP hardware",
        "Robotics and autonomous systems",
        "VR game design with adaptive difficulty",
        "Statistical modeling and experimental paradigm design",
        "Error propagation testing",
    ],
    "notable_projects": [
        "AstraZeneca Medical Virtual Assistant (AIMI) - GenAI ML for clinical applications",
        "Nature Machine Intelligence publication - Robot that learns locomotion autonomously",
        "NIH SBIR direct-to-phase-II grant as PI for osteoarthritis clinical trial",
        "AWS pipeline + FastAPI dashboard + Django clinician interface for medical device",
        "Neurophysiological algorithm for muscle signal interpretation",
        "VR adaptive difficulty game design",
    ],
    "technologies": [
        "Python", "AWS", "FastAPI", "Django", "Machine Learning", "GenAI", "LLM",
        "NLP", "Deep Learning", "Reinforcement Learning", "Signal Processing",
        "Cloud Architecture", "Docker", "Statistical Modeling", "XGBoost",
        "Neural Networks", "Computer Vision", "VR/AR",
    ],
    "domains": [
        "Healthcare", "Biotechnology", "Pharmaceutical", "Medical Devices",
        "Neuroscience", "Robotics", "Life Sciences", "Clinical Trials",
    ],
    "awards": [
        "USC Health Technology Innovation Fellowship",
        "USC Viterbi PhD Merit Fellowship",
        "Howard Hughes Medical Institute Research Grant",
        "368 research citations",
    ],
    "interests_keywords": [
        "machine learning", "AI", "generative AI", "healthcare", "biotech",
        "medical", "clinical", "neural", "robotics", "autonomous",
        "prediction", "forecasting", "NLP", "chatbot", "RAG",
        "data strategy", "innovation", "research", "science",
        "product development", "human-in-the-loop", "adaptive",
        "signal processing", "optimization", "anomaly detection",
        "deep learning", "reinforcement learning",
    ]
}


def score_case_study_interest(doc):
    """Score how interesting/innovative a case study would be for Brian."""
    score = 0
    text = " ".join([
        doc.get("title", "") or "",
        doc.get("challenge", "") or "",
        doc.get("solution", "") or "",
        doc.get("results", "") or "",
        doc.get("technologies", "") or "",
        doc.get("full_text", "") or "",
    ]).lower()

    # Innovation markers (higher weight)
    innovation_terms = [
        ("generative ai", 15), ("genai", 15), ("llm", 14), ("rag", 14),
        ("machine learning", 12), ("ml", 10), ("ai", 8),
        ("chatbot", 12), ("nlp", 12), ("natural language", 12),
        ("predictive", 10), ("prediction", 10), ("forecasting", 10),
        ("autonomous", 12), ("agentic", 14), ("agent", 10),
        ("knowledge graph", 14), ("neural", 10), ("deep learning", 12),
        ("xgboost", 10), ("prophet", 8), ("feature store", 10),
        ("sentiment analysis", 10), ("anomaly detection", 12),
        ("snowpark", 8), ("native app", 8),
        ("real-time", 6), ("automation", 5), ("optimization", 5),
    ]
    for term, weight in innovation_terms:
        if term in text:
            score += weight

    # Domain alignment with Brian's background
    domain_terms = [
        ("healthcare", 8), ("medical", 8), ("clinical", 8),
        ("pharmaceutical", 7), ("biotech", 7), ("pharma", 7),
        ("life science", 7), ("patient", 6),
        ("research", 5), ("science", 4),
        ("education", 4), ("learning platform", 5),
    ]
    for term, weight in domain_terms:
        if term in text:
            score += weight

    # Technology alignment
    tech_terms = [
        ("python", 4), ("aws", 4), ("fastapi", 5), ("django", 5),
        ("snowflake", 2), ("dbt", 2), ("airflow", 3),
        ("databricks", 3), ("sagemaker", 5), ("bedrock", 5),
    ]
    for term, weight in tech_terms:
        if term in text:
            score += weight

    # Penalize pure migration/basic BI stories (less innovative)
    boring_terms = [
        ("migrates to snowflake", -5), ("migration", -3),
        ("power bi implementation", -4), ("tableau migration", -4),
        ("cost savings", -2), ("cost optimization", -2),
    ]
    for term, weight in boring_terms:
        if term in text:
            score += weight

    return score


def score_case_study_contribution(doc):
    """Score how likely Brian could contribute to a similar project."""
    score = 0
    text = " ".join([
        doc.get("title", "") or "",
        doc.get("challenge", "") or "",
        doc.get("solution", "") or "",
        doc.get("results", "") or "",
        doc.get("technologies", "") or "",
        doc.get("full_text", "") or "",
    ]).lower()

    # Direct skill match (Brian has these skills)
    skill_matches = [
        ("machine learning", 15), ("ml", 12), ("generative ai", 15),
        ("genai", 15), ("llm", 14), ("ai", 8),
        ("chatbot", 12), ("rag", 14), ("nlp", 12),
        ("predictive", 12), ("prediction", 12), ("forecasting", 10),
        ("anomaly detection", 12), ("sentiment analysis", 10),
        ("xgboost", 12), ("prophet", 10), ("feature store", 10),
        ("knowledge graph", 14), ("neural", 10),
        ("python", 8), ("aws", 8), ("fastapi", 6),
        ("agentic", 14), ("agent", 8), ("autonomous", 10),
        ("human-in-the-loop", 15), ("adaptive", 8),
    ]
    for term, weight in skill_matches:
        if term in text:
            score += weight

    # Healthcare/life science domain (Brian's primary domain)
    healthcare_terms = [
        ("healthcare", 12), ("medical", 12), ("clinical", 12),
        ("pharmaceutical", 10), ("biotech", 10), ("pharma", 10),
        ("patient", 8), ("health", 6), ("life science", 10),
        ("sleep apnea", 12), ("cancer", 8), ("dental", 6),
    ]
    for term, weight in healthcare_terms:
        if term in text:
            score += weight

    # Research/science alignment
    research_terms = [
        ("research", 6), ("algorithm", 8), ("model", 4),
        ("data strategy", 6), ("architecture", 5),
        ("product", 4), ("innovation", 5),
    ]
    for term, weight in research_terms:
        if term in text:
            score += weight

    # Penalize areas far from Brian's expertise
    mismatch_terms = [
        ("sap data", -5), ("tableau dashboard", -4),
        ("power bi premium", -5), ("alteryx workflow", -3),
        ("sustainability reporting", -4), ("new hire documentation", -5),
        ("commercial lending report", -4),
    ]
    for term, weight in mismatch_terms:
        if term in text:
            score += weight

    return score


def generate_narrative_interesting(case_studies):
    """Generate narrative for top 10 most interesting case studies."""
    lines = []
    lines.append("# Top 10 Most Interesting & Innovative phData Case Studies")
    lines.append(f"## Curated for Brian Cohn, Ph.D.\n")
    lines.append("These case studies represent the most technically innovative and intellectually")
    lines.append("stimulating projects from phData's portfolio, selected based on their use of")
    lines.append("cutting-edge technologies (GenAI, ML, knowledge graphs, agentic AI), novel")
    lines.append("problem-solving approaches, and alignment with emerging trends in AI/ML.\n")
    lines.append("---\n")

    for i, (score, doc) in enumerate(case_studies, 1):
        lines.append(f"### {i}. {doc['title']}")
        lines.append(f"**Industry:** {doc.get('industry', 'N/A')}  ")
        lines.append(f"**Innovation Score:** {score}  ")
        lines.append(f"**Technologies:** {doc.get('technologies', 'N/A')}  ")
        lines.append(f"**URL:** {doc['url']}\n")

        if doc.get("challenge"):
            lines.append(f"**The Challenge:** {doc['challenge'][:500]}\n")
        if doc.get("solution"):
            lines.append(f"**The Solution:** {doc['solution'][:500]}\n")
        if doc.get("results"):
            lines.append(f"**The Results:** {doc['results'][:500]}\n")

        # Why it's interesting
        reasons = []
        text = (doc.get("full_text") or "").lower()
        if any(t in text for t in ["genai", "generative ai", "llm"]):
            reasons.append("Leverages generative AI/LLM technology at the frontier of enterprise AI adoption")
        if any(t in text for t in ["rag", "chatbot"]):
            reasons.append("Implements RAG or conversational AI, a rapidly evolving architectural pattern")
        if any(t in text for t in ["knowledge graph", "knowledge"]):
            reasons.append("Uses knowledge graphs, combining structured and unstructured data in novel ways")
        if any(t in text for t in ["agentic", "agent"]):
            reasons.append("Explores agentic AI patterns, representing the next wave of AI automation")
        if any(t in text for t in ["machine learning", "ml", "predictive"]):
            reasons.append("Applies machine learning for predictive analytics and intelligent automation")
        if any(t in text for t in ["healthcare", "medical", "pharma"]):
            reasons.append("Addresses challenges in healthcare/life sciences, where data-driven solutions have outsized impact")
        if any(t in text for t in ["anomaly", "detection"]):
            reasons.append("Tackles anomaly detection, a technically rich problem space")
        if any(t in text for t in ["sentiment", "nlp", "natural language"]):
            reasons.append("Applies NLP/sentiment analysis, bridging unstructured text and actionable insights")

        if reasons:
            lines.append("**Why This Is Interesting:**")
            for r in reasons:
                lines.append(f"- {r}")
            lines.append("")

        lines.append("---\n")

    # Thematic narrative
    lines.append("## Overarching Themes\n")
    lines.append("Across these top 10 case studies, several themes emerge that define the cutting edge")
    lines.append("of enterprise data and AI consulting:\n")
    lines.append("1. **Generative AI is Reshaping Enterprise Operations** - From RAG-powered contract inquiry")
    lines.append("   chatbots to agentic AI for procurement automation, GenAI is moving beyond proof-of-concept")
    lines.append("   into production workloads that deliver measurable ROI.\n")
    lines.append("2. **AI + Domain Expertise = Transformative Impact** - The most compelling case studies")
    lines.append("   combine ML/AI with deep domain knowledge (healthcare, finance, education), creating")
    lines.append("   solutions that couldn't exist with either alone.\n")
    lines.append("3. **The Data Platform as AI Foundation** - Modern AI applications require robust data")
    lines.append("   platforms. Several studies show how Snowflake, dbt, and cloud-native architectures")
    lines.append("   provide the foundation that makes advanced analytics and AI possible.\n")
    lines.append("4. **From Prediction to Prescription to Automation** - The trajectory is clear: from")
    lines.append("   predictive models (anomaly detection, demand forecasting) to prescriptive analytics")
    lines.append("   (recommendations) to fully autonomous AI agents.\n")
    lines.append("5. **Healthcare and Life Sciences as AI Frontier** - Multiple case studies in healthcare")
    lines.append("   demonstrate that the intersection of AI and clinical/life science data remains one of")
    lines.append("   the most impactful and technically challenging domains.\n")

    return "\n".join(lines)


def generate_narrative_contribution(case_studies):
    """Generate narrative for top 5 case studies Brian could contribute to."""
    lines = []
    lines.append("# Top 5 phData Case Studies Where Brian Cohn Could Contribute Most")
    lines.append(f"## Skills-to-Project Alignment Analysis\n")
    lines.append("These case studies represent the strongest alignment between Brian Cohn's unique")
    lines.append("combination of skills---machine learning, healthcare/biotech domain expertise,")
    lines.append("GenAI architecture, clinical trial experience, and product development---and the")
    lines.append("technical challenges phData solved for their clients.\n")
    lines.append("---\n")

    for i, (score, doc) in enumerate(case_studies, 1):
        lines.append(f"### {i}. {doc['title']}")
        lines.append(f"**Industry:** {doc.get('industry', 'N/A')}  ")
        lines.append(f"**Contribution Score:** {score}  ")
        lines.append(f"**Technologies:** {doc.get('technologies', 'N/A')}  ")
        lines.append(f"**URL:** {doc['url']}\n")

        if doc.get("challenge"):
            lines.append(f"**The Challenge:** {doc['challenge'][:500]}\n")
        if doc.get("solution"):
            lines.append(f"**The Solution:** {doc['solution'][:500]}\n")
        if doc.get("results"):
            lines.append(f"**The Results:** {doc['results'][:500]}\n")

        # How Brian could contribute
        contributions = []
        text = (doc.get("full_text") or "").lower()

        if any(t in text for t in ["genai", "generative ai", "llm", "rag", "chatbot"]):
            contributions.append(
                "**GenAI Architecture & Implementation:** Brian's experience as Sr. Architect at Credera "
                "leading GenAI initiatives (including the AstraZeneca AIMI virtual assistant) directly "
                "maps to the LLM/GenAI components of this project. He could contribute production-grade "
                "prompt engineering, RAG pipeline optimization, and evaluation frameworks."
            )
        if any(t in text for t in ["machine learning", "ml", "predictive", "prediction", "xgboost", "prophet"]):
            contributions.append(
                "**ML Model Development & Deployment:** With a Ph.D. in CS from USC Viterbi and "
                "publications in Nature Machine Intelligence, Brian brings rigorous ML methodology. "
                "He could improve model selection, feature engineering, and validation approaches."
            )
        if any(t in text for t in ["healthcare", "medical", "clinical", "pharma", "biotech", "patient"]):
            contributions.append(
                "**Healthcare Domain Expertise:** As a researcher who has led NIH-funded clinical trials "
                "and built medical device platforms, Brian understands the unique constraints of healthcare "
                "data---HIPAA compliance, clinical validation requirements, and the gap between research "
                "and clinical deployment."
            )
        if any(t in text for t in ["aws", "cloud", "pipeline", "architecture"]):
            contributions.append(
                "**Cloud Architecture & Pipeline Design:** Brian has built production AWS pipelines with "
                "FastAPI and Django for medical applications. He could contribute to architectural decisions, "
                "API design, and ensuring the data platform supports ML workloads at scale."
            )
        if any(t in text for t in ["anomaly", "detection", "signal", "sensor"]):
            contributions.append(
                "**Signal Processing & Anomaly Detection:** Brian's background in neurophysiological "
                "signal analysis and closed-loop DSP hardware gives him unique expertise in detecting "
                "patterns in noisy data---directly applicable to anomaly detection use cases."
            )
        if any(t in text for t in ["agentic", "agent", "autonomous", "automation"]):
            contributions.append(
                "**Agentic AI & Autonomous Systems:** Brian's Nature Machine Intelligence publication "
                "on autonomous robot learning demonstrates expertise in systems that learn and adapt "
                "without explicit programming---the core principle behind modern agentic AI."
            )
        if any(t in text for t in ["knowledge graph", "knowledge", "curriculum"]):
            contributions.append(
                "**Knowledge Representation & Learning Systems:** Brian's research in computational "
                "neuroscience and his experience with adaptive learning systems (VR game design with "
                "adaptive difficulty) make him well-suited for knowledge graph and learning platform projects."
            )
        if any(t in text for t in ["data strategy", "strategy", "roadmap"]):
            contributions.append(
                "**Data & AI Strategy:** As both a researcher and product builder, Brian bridges the gap "
                "between cutting-edge AI research and practical business applications. He could contribute "
                "to defining AI roadmaps grounded in what's technically feasible and commercially viable."
            )
        if any(t in text for t in ["sentiment", "nlp", "natural language", "text"]):
            contributions.append(
                "**NLP & Text Analytics:** Brian's GenAI work at Credera and research background in "
                "computational methods make him well-positioned to architect NLP solutions that go beyond "
                "surface-level text analysis to extract deep, domain-specific insights."
            )
        if any(t in text for t in ["feature store", "feature"]):
            contributions.append(
                "**ML Infrastructure & Feature Engineering:** Brian's experience building production ML "
                "systems means he understands the importance of feature stores, experiment tracking, and "
                "ML ops---critical infrastructure for scaling ML in enterprise settings."
            )

        if contributions:
            lines.append("**How Brian Could Contribute:**\n")
            for c in contributions:
                lines.append(f"- {c}\n")

        lines.append("---\n")

    # Overarching contribution narrative
    lines.append("## Brian Cohn's Unique Value Proposition for phData\n")
    lines.append("Across these five case studies, a clear pattern emerges: the projects where Brian")
    lines.append("could contribute the most sit at the intersection of **advanced AI/ML** and")
    lines.append("**domain-specific expertise**, particularly in healthcare and life sciences.\n")
    lines.append("### The Differentiators\n")
    lines.append("1. **Research-to-Production Pipeline:** Unlike many ML practitioners who operate")
    lines.append("   exclusively in either research or production, Brian has done both---from publishing")
    lines.append("   in Nature Machine Intelligence to shipping clinical-grade medical device software.")
    lines.append("   This means he can evaluate bleeding-edge techniques AND deploy them reliably.\n")
    lines.append("2. **Healthcare AI Expertise:** With an NIH SBIR grant as PI, clinical trial design")
    lines.append("   experience, and medical device development background, Brian brings credibility")
    lines.append("   and domain knowledge that's essential for healthcare AI projects where the stakes")
    lines.append("   (patient outcomes, regulatory compliance) are highest.\n")
    lines.append("3. **GenAI at Enterprise Scale:** His current role at Credera leading GenAI initiatives")
    lines.append("   (including the AstraZeneca AIMI project) means he's solving exactly the problems")
    lines.append("   phData's clients face: how to move GenAI from impressive demos to production systems")
    lines.append("   that deliver measurable business value.\n")
    lines.append("4. **Interdisciplinary Problem Solving:** Brian's combination of CS, neuroscience,")
    lines.append("   robotics, and healthcare creates a rare ability to see connections across domains---")
    lines.append("   the kind of thinking that produces novel solutions to complex enterprise challenges.\n")
    lines.append("5. **Human-in-the-Loop Design Philosophy:** From adaptive VR games to clinical")
    lines.append("   interfaces, Brian consistently designs systems where AI augments human decision-making")
    lines.append("   rather than replacing it---a philosophy that leads to higher adoption and trust")
    lines.append("   in enterprise AI deployments.\n")

    return "\n".join(lines)


def main():
    engine = PhDataSearchEngine()
    all_cases = engine.get_all_case_studies()

    if not all_cases:
        print("ERROR: No case studies found. Run scraper.py first.")
        return

    print(f"Analyzing {len(all_cases)} case studies against Brian Cohn's profile...\n")

    # Score all case studies for both dimensions
    interest_scores = [(score_case_study_interest(doc), doc) for doc in all_cases]
    contribution_scores = [(score_case_study_contribution(doc), doc) for doc in all_cases]

    # Sort by score descending
    interest_scores.sort(key=lambda x: x[0], reverse=True)
    contribution_scores.sort(key=lambda x: x[0], reverse=True)

    # Top 10 most interesting
    top_10_interesting = interest_scores[:10]
    print("=== Top 10 Most Interesting/Innovative Case Studies ===")
    for i, (score, doc) in enumerate(top_10_interesting, 1):
        print(f"  {i}. [{score}] {doc['title']}")
        print(f"     Tech: {doc.get('technologies', 'N/A')}")

    print()

    # Top 5 best contribution fit
    top_5_contribute = contribution_scores[:5]
    print("=== Top 5 Case Studies Brian Could Contribute To ===")
    for i, (score, doc) in enumerate(top_5_contribute, 1):
        print(f"  {i}. [{score}] {doc['title']}")
        print(f"     Tech: {doc.get('technologies', 'N/A')}")

    # Generate narratives
    print("\nGenerating narratives...")

    narrative_interesting = generate_narrative_interesting(top_10_interesting)
    interesting_path = os.path.join(OUTPUT_DIR, "top_10_interesting_case_studies.md")
    with open(interesting_path, "w") as f:
        f.write(narrative_interesting)
    print(f"  Written: {interesting_path}")

    narrative_contribute = generate_narrative_contribution(top_5_contribute)
    contribute_path = os.path.join(OUTPUT_DIR, "top_5_contribution_fit.md")
    with open(contribute_path, "w") as f:
        f.write(narrative_contribute)
    print(f"  Written: {contribute_path}")

    # Also write a combined executive summary
    summary_lines = []
    summary_lines.append("# phData Experience Analysis: Brian Cohn, Ph.D.")
    summary_lines.append(f"## Executive Summary\n")
    summary_lines.append(f"Analyzed {len(all_cases)} phData case studies against Brian Cohn's profile.\n")
    summary_lines.append("### Quick Reference\n")
    summary_lines.append("| File | Description |")
    summary_lines.append("|------|-------------|")
    summary_lines.append("| `top_10_interesting_case_studies.md` | 10 most innovative/interesting case studies with thematic analysis |")
    summary_lines.append("| `top_5_contribution_fit.md` | 5 case studies with strongest skills alignment + contribution narratives |")
    summary_lines.append("| `phdata_cases.db` | SQLite database with all case studies, FTS5 index, and Google results |")
    summary_lines.append("| `search_engine.py` | BM25 + FTS5 search engine (run interactively) |")
    summary_lines.append("| `scraper.py` | Case study scraper with Google site search module |")
    summary_lines.append("")
    summary_lines.append("### Top 10 Most Interesting (by Innovation Score)\n")
    for i, (score, doc) in enumerate(top_10_interesting, 1):
        summary_lines.append(f"{i}. **{doc['title']}** (score: {score}) - {doc.get('industry', 'N/A')}")
    summary_lines.append("")
    summary_lines.append("### Top 5 Contribution Fit (by Skills Alignment Score)\n")
    for i, (score, doc) in enumerate(top_5_contribute, 1):
        summary_lines.append(f"{i}. **{doc['title']}** (score: {score}) - {doc.get('industry', 'N/A')}")
    summary_lines.append("")
    summary_lines.append("### Brian Cohn's Key Strengths for phData Projects\n")
    summary_lines.append("- GenAI/LLM architecture and deployment (Credera Sr. Architect, AstraZeneca AIMI)")
    summary_lines.append("- Healthcare/life sciences domain expertise (NIH SBIR PI, clinical trials)")
    summary_lines.append("- ML research-to-production (Nature Machine Intelligence, shipped medical device software)")
    summary_lines.append("- AWS cloud architecture (FastAPI, Django, production pipelines)")
    summary_lines.append("- Human-in-the-loop AI system design")
    summary_lines.append("- Interdisciplinary problem solving (CS + neuroscience + robotics + healthcare)")

    summary_path = os.path.join(OUTPUT_DIR, "SUMMARY.md")
    with open(summary_path, "w") as f:
        f.write("\n".join(summary_lines))
    print(f"  Written: {summary_path}")

    engine.close()
    print("\nDone! All narratives generated.")


if __name__ == "__main__":
    main()

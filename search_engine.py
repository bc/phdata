#!/usr/bin/env python3
"""BM25 search engine for phData case studies + SQLite FTS5 fallback."""

import sqlite3
import re
import os
from rank_bm25 import BM25Okapi

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phdata_cases.db")


def tokenize(text):
    """Simple tokenizer: lowercase, split on non-alphanumeric, remove stopwords."""
    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                 "of", "with", "by", "from", "is", "was", "are", "were", "been", "be",
                 "have", "has", "had", "do", "does", "did", "will", "would", "could",
                 "should", "may", "might", "shall", "can", "this", "that", "these",
                 "those", "it", "its", "they", "their", "them", "we", "our", "us",
                 "he", "she", "his", "her", "i", "me", "my", "you", "your"}
    tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
    return [t for t in tokens if t not in stopwords and len(t) > 1]


class PhDataSearchEngine:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._load_corpus()

    def _load_corpus(self):
        """Load all case studies and build BM25 index."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM case_studies ORDER BY id")
        self.documents = [dict(row) for row in c.fetchall()]

        # Build combined text for each document
        self.corpus_texts = []
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
            self.corpus_texts.append(combined)

        # Tokenize and build BM25
        tokenized = [tokenize(text) for text in self.corpus_texts]
        self.bm25 = BM25Okapi(tokenized)
        print(f"BM25 index built with {len(self.documents)} documents")

    def search_bm25(self, query, top_k=10):
        """Search using BM25 ranking."""
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        # Pair scores with documents
        scored_docs = list(zip(scores, self.documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored_docs[:top_k]:
            if score > 0:
                results.append({"score": round(score, 4), **doc})
        return results

    def search_fts(self, query, top_k=10):
        """Search using SQLite FTS5 (exact phrase matching)."""
        c = self.conn.cursor()
        try:
            c.execute("""SELECT cs.*, rank FROM case_studies_fts fts
                JOIN case_studies cs ON cs.id = fts.rowid
                WHERE case_studies_fts MATCH ?
                ORDER BY rank LIMIT ?""", (query, top_k))
            return [dict(row) for row in c.fetchall()]
        except Exception:
            return []

    def search(self, query, top_k=10, method="bm25"):
        """Unified search interface."""
        if method == "fts":
            return self.search_fts(query, top_k)
        return self.search_bm25(query, top_k)

    def get_all_case_studies(self):
        """Return all case studies."""
        return self.documents

    def get_case_study(self, case_id):
        """Get a single case study by ID."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM case_studies WHERE id = ?", (case_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def get_technologies_summary(self):
        """Get a summary of all technologies used across case studies."""
        tech_count = {}
        for doc in self.documents:
            techs = (doc.get("technologies") or "").split(", ")
            for t in techs:
                t = t.strip()
                if t:
                    tech_count[t] = tech_count.get(t, 0) + 1
        return sorted(tech_count.items(), key=lambda x: x[1], reverse=True)

    def get_industries_summary(self):
        """Get a summary of industries represented."""
        ind_count = {}
        for doc in self.documents:
            ind = (doc.get("industry") or "Unknown").strip()
            if ind:
                ind_count[ind] = ind_count.get(ind, 0) + 1
        return sorted(ind_count.items(), key=lambda x: x[1], reverse=True)

    def close(self):
        self.conn.close()


def main():
    """Interactive search CLI."""
    engine = PhDataSearchEngine()

    print("\n=== phData Case Study Search Engine ===")
    print(f"Loaded {len(engine.documents)} case studies")
    print("\nTechnologies breakdown:")
    for tech, count in engine.get_technologies_summary()[:15]:
        print(f"  {tech}: {count}")
    print("\nIndustries breakdown:")
    for ind, count in engine.get_industries_summary():
        print(f"  {ind}: {count}")

    print("\nType a search query (or 'quit' to exit):")
    while True:
        query = input("\n> ").strip()
        if query.lower() in ("quit", "exit", "q"):
            break
        results = engine.search(query, top_k=5)
        if not results:
            print("No results found.")
            continue
        for i, r in enumerate(results, 1):
            print(f"\n--- Result {i} (score: {r.get('score', 'N/A')}) ---")
            print(f"Title: {r['title']}")
            print(f"Industry: {r.get('industry', 'N/A')}")
            print(f"Technologies: {r.get('technologies', 'N/A')}")
            print(f"URL: {r['url']}")
            challenge = (r.get('challenge') or '')[:200]
            if challenge:
                print(f"Challenge: {challenge}...")

    engine.close()


if __name__ == "__main__":
    main()

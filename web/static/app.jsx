const { useState, useEffect, useRef, useCallback } = React;

// ---- Icons ----

const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
  </svg>
);

const ArrowIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
  </svg>
);

const DbIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>
  </svg>
);

const ExternalIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
  </svg>
);

const CartIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
  </svg>
);

const TrashIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
);

const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

// ---- App ----

function App() {
  const [view, setView] = useState("dashboard");
  const [stats, setStats] = useState(null);
  const [cases, setCases] = useState([]);
  const [brianFit, setBrianFit] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [selectedCase, setSelectedCase] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cart, setCart] = useState([]); // [{...caseData, cartNote: ""}]
  const searchRef = useRef(null);
  const debounce = useRef(null);

  const addToCart = useCallback((caseData) => {
    setCart(prev => {
      if (prev.find(c => c.id === caseData.id)) return prev;
      return [...prev, { ...caseData, cartNote: "" }];
    });
  }, []);

  const removeFromCart = useCallback((id) => {
    setCart(prev => prev.filter(c => c.id !== id));
  }, []);

  const updateCartNote = useCallback((id, note) => {
    setCart(prev => prev.map(c => c.id === id ? { ...c, cartNote: note } : c));
  }, []);

  const isInCart = useCallback((id) => cart.some(c => c.id === id), [cart]);

  useEffect(() => {
    Promise.all([
      fetch("/api/stats").then(r => r.json()),
      fetch("/api/case-studies?limit=76").then(r => r.json()),
      fetch("/api/brian-fit").then(r => r.json()),
    ]).then(([s, c, b]) => {
      setStats(s);
      setCases(c.results);
      setBrianFit(b);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === "/" && document.activeElement.tagName !== "INPUT") {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (e.key === "Escape") {
        setSelectedCase(null);
        if (searchQuery) { setSearchResults(null); setSearchQuery(""); }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [searchQuery]);

  const handleSearch = useCallback((q) => {
    setSearchQuery(q);
    clearTimeout(debounce.current);
    if (!q.trim()) { setSearchResults(null); return; }
    debounce.current = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(q)}&limit=20`)
        .then(r => r.json())
        .then(data => { setSearchResults(data.results); setView("search"); });
    }, 200);
  }, []);

  const navigate = useCallback((v) => {
    setView(v);
    setSearchQuery("");
    setSearchResults(null);
  }, []);

  if (loading) return <div className="loading"><div className="spinner" />Loading...</div>;

  // Full-screen views: no hero/statbar/footer
  if (view === "projector") {
    return (
      <>
        <Nav view={view} navigate={navigate} />
        <Projector />
      </>
    );
  }

  if (view === "prospects") {
    return (
      <>
        <Nav view={view} navigate={navigate} />
        <ProspectMap />
      </>
    );
  }

  return (
    <>
      <Nav view={view} navigate={navigate} cartCount={cart.length} onCartClick={() => navigate("cart")} />
      <Hero query={searchQuery} onSearch={handleSearch} inputRef={searchRef} />
      <StatBar stats={stats} />
      <div className="content">
        {view === "search" && searchResults && <SearchResults results={searchResults} query={searchQuery} onSelect={setSelectedCase} addToCart={addToCart} isInCart={isInCart} />}
        {view === "dashboard" && <Dashboard stats={stats} fit={brianFit} onSelect={setSelectedCase} />}
        {view === "cases" && <CaseStudies cases={cases} onSelect={setSelectedCase} addToCart={addToCart} isInCart={isInCart} />}
        {view === "fit" && brianFit && <FitView fit={brianFit} />}
        {view === "analytics" && stats && <Analytics stats={stats} />}
        {view === "cart" && <CartView cart={cart} removeFromCart={removeFromCart} updateCartNote={updateCartNote} />}
      </div>
      <Footer />
      {selectedCase && <Modal data={selectedCase} onClose={() => setSelectedCase(null)} addToCart={addToCart} isInCart={isInCart} />}
    </>
  );
}

// ---- Nav ----

function Nav({ view, navigate, cartCount = 0, onCartClick }) {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <a className="nav-logo" href="#" onClick={e => { e.preventDefault(); navigate("dashboard"); }}>
          <img src="/static/logos/phdata.png" alt="phData" className="nav-logo-img" />
          <span className="nav-logo-divider" />
          <span className="nav-logo-label">Experience Portal</span>
        </a>
        <div className="nav-links">
          {[["dashboard","Dashboard"],["cases","Case Studies"],["fit","Brian's Fit"],["analytics","Analytics"],["projector","Projector"],["prospects","Prospects"]].map(([key,label]) => (
            <button key={key} className={`nav-link ${view === key ? "active" : ""}`} onClick={() => navigate(key)} aria-label={`Navigate to ${label}`} aria-current={view === key ? "page" : undefined}>{label}</button>
          ))}
          <button className="nav-cart-btn" onClick={onCartClick} aria-label="Open research cart" title="Research Cart">
            <CartIcon size={16} />
            {cartCount > 0 && <span className="nav-cart-badge">{cartCount}</span>}
          </button>
        </div>
      </div>
    </nav>
  );
}

// ---- Hero ----

function Hero({ query, onSearch, inputRef }) {
  return (
    <div className="hero">
      <div className="hero-content">
        <h1>Search <span>76 Case Studies</span> Instantly</h1>
        <p>BM25-ranked search across phData's full portfolio</p>
        <div className="hero-byline">Built by Brian Cohn — ML Engineer, Healthcare + GenAI Specialist</div>
        <div className="search-container">
          <div className="search-input-wrap">
            <span className="search-icon"><SearchIcon /></span>
            <input ref={inputRef} className="search-input" type="text"
              placeholder='Try "generative AI healthcare" or "snowflake migration"'
              value={query} onChange={e => onSearch(e.target.value)}
              aria-label="Search case studies" />
            <span className="search-kbd">/</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Stat Bar ----

function StatBar({ stats }) {
  if (!stats) return null;
  const topIndustries = stats.industries.slice(0, 3).map(([n]) => n).join(", ");
  const topTechs = stats.technologies.slice(0, 3).map(([n]) => n).join(", ");
  const items = [
    [stats.total_case_studies, "Case Studies", `Across ${stats.industries.length} industries`],
    [stats.industries.length, "Industries", `Top: ${topIndustries}`],
    [stats.technologies.length, "Technologies", `Top: ${topTechs}`],
    [stats.technologies[0]?.[0] || "—", "Top Tech", `${stats.technologies[0]?.[1] || 0} case studies`],
  ];
  return (
    <div className="stat-bar">
      <div className="stat-bar-inner">
        {items.map(([val, label, tooltip], i) => (
          <div className="stat-item" key={i} title={tooltip}>
            <div className="stat-value">{val}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Dashboard ----

function Dashboard({ stats, fit, onSelect }) {
  return (
    <>
      <section className="section">
        <div className="section-header">
          <div>
            <div className="section-title">Brian Cohn's Top Contribution Matches</div>
            <div className="section-subtitle">Strongest alignment to ML, healthcare, and GenAI expertise</div>
          </div>
        </div>
        {fit?.top_5_contribution.map((item, i) => (
          <FitCard key={i} item={item} field="match" label="Score" />
        ))}
      </section>

      <section className="section">
        <div className="two-col">
          <div className="chart-panel">
            <div className="chart-panel-title">Industry Distribution</div>
            <BarChart data={stats.industries.slice(0, 8)} max={stats.industries[0]?.[1]} />
          </div>
          <div className="chart-panel">
            <div className="chart-panel-title">Technology Landscape</div>
            <BarChart data={stats.technologies.slice(0, 8)} max={stats.technologies[0]?.[1]} alt />
          </div>
        </div>
      </section>
    </>
  );
}

// ---- Fit Card ----

function FitCard({ item, field, label }) {
  return (
    <div className="fit-card">
      <div className="fit-rank">{item.rank}</div>
      <div className="fit-body">
        <div className="fit-title">{item.title}</div>
        <div className="fit-reason">{item[field]}</div>
        <div className="card-meta" style={{ marginTop: 6 }}>
          <span className="badge badge-industry">{item.industry}</span>
        </div>
      </div>
      <div className="fit-score-bar">
        <div className="fit-score-num">{item.score}</div>
        <div className="fit-score-label">{label}</div>
      </div>
    </div>
  );
}

// ---- Bar Chart ----

function BarChart({ data, max, alt }) {
  return (
    <div className="bar-chart">
      {data.map(([name, count], i) => (
        <div className="bar-row" key={i}>
          <div className="bar-label">{name}</div>
          <div className="bar-track">
            <div className={`bar-fill ${alt ? "bar-fill-alt" : ""}`}
              style={{ width: `${Math.max((count / max) * 100, 8)}%` }}>
              <span className="bar-value">{count}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---- Search Results ----

function SearchResults({ results, query, onSelect, addToCart, isInCart }) {
  if (!results.length) {
    return <section className="section"><div className="empty"><div className="empty-icon">&#8709;</div>No results for "{query}"</div></section>;
  }
  return (
    <section className="section">
      <div className="section-header">
        <div>
          <div className="section-title">{results.length} results for "{query}"</div>
          <div className="section-subtitle">Ranked by BM25 relevance</div>
        </div>
      </div>
      <div className="card-grid">
        {results.map((r, i) => <CaseCard key={r.id} data={r} onSelect={onSelect} showScore isTopMatch={i < 3} animDelay={i * 60} addToCart={addToCart} isInCart={isInCart} />)}
      </div>
    </section>
  );
}

// ---- Case Studies List ----

function CaseStudies({ cases, onSelect, addToCart, isInCart }) {
  const [filter, setFilter] = useState("All");
  const industries = ["All", ...new Set(cases.map(c => c.industry).filter(Boolean).sort())];
  const filtered = filter === "All" ? cases : cases.filter(c => c.industry === filter);

  return (
    <section className="section">
      <div className="section-header">
        <div>
          <div className="section-title">All Case Studies</div>
          <div className="section-subtitle">{filtered.length} of {cases.length}</div>
        </div>
      </div>
      <div className="tab-bar" style={{ overflowX: "auto" }}>
        {industries.slice(0, 8).map(ind => (
          <button key={ind} className={`tab ${filter === ind ? "active" : ""}`} onClick={() => setFilter(ind)}>{ind}</button>
        ))}
      </div>
      <div className="card-grid">
        {filtered.map(c => <CaseCard key={c.id} data={c} onSelect={onSelect} addToCart={addToCart} isInCart={isInCart} />)}
      </div>
    </section>
  );
}

// ---- Case Card ----

function CaseCard({ data, onSelect, showScore, isTopMatch, animDelay, addToCart, isInCart }) {
  const techs = (data.technologies || "").split(", ").filter(Boolean).slice(0, 4);
  const scoreClass = (data.score || 0) > 3 ? "score-high" : (data.score || 0) > 1 ? "score-med" : "score-low";
  const excerpt = data.challenge || data.client || data.full_text || "";
  const inCart = isInCart && isInCart(data.id);

  return (
    <div className={`card ${isTopMatch ? "card-top-match" : ""}`} onClick={() => onSelect(data)}
      style={animDelay != null ? { animation: `cardFadeIn 300ms ${animDelay}ms both` } : undefined}>
      <div className="card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div className="card-title">{data.title}</div>
          {isTopMatch && <span className="top-match-badge">Top Match</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {showScore && data.score != null && <span className={`card-score ${scoreClass}`}>{data.score}</span>}
          {addToCart && (
            <button
              className={`cart-add-btn ${inCart ? "in-cart" : ""}`}
              onClick={e => { e.stopPropagation(); if (!inCart) addToCart(data); }}
              title={inCart ? "In cart" : "Add to research cart"}
              aria-label={inCart ? "Already in cart" : "Add to research cart"}
            >
              {inCart ? <CheckIcon /> : <PlusIcon />}
            </button>
          )}
        </div>
      </div>
      <div className="card-meta">
        {data.industry && <span className="badge badge-industry">{data.industry}</span>}
      </div>
      {excerpt && <div className="card-text">{excerpt}</div>}
      <div className="card-footer">
        <div className="tech-list">
          {techs.map((t, i) => <span key={i} className="tech-tag">{t}</span>)}
        </div>
        <span className="card-link">View <ArrowIcon /></span>
      </div>
    </div>
  );
}

// ---- Fit View ----

function FitView({ fit }) {
  return (
    <>
      <section className="section">
        <div className="section-header">
          <div>
            <div className="section-title">Top 10 Most Interesting & Innovative</div>
            <div className="section-subtitle">GenAI, ML, knowledge graphs, agentic AI, novel approaches</div>
          </div>
        </div>
        {fit.top_10_interesting.map((item, i) => <FitCard key={i} item={item} field="why" label="Innovation" />)}
      </section>
      <div className="fit-divider">
        <div className="fit-divider-line" />
        <div className="fit-divider-label">Contribution Analysis</div>
        <div className="fit-divider-line" />
      </div>
      <section className="section" style={{ paddingTop: 24 }}>
        <div className="section-header">
          <div>
            <div className="section-title">Top 5 Contribution Fit</div>
            <div className="section-subtitle">Where Brian's skills create the most value — ranked by direct expertise alignment</div>
          </div>
        </div>
        {fit.top_5_contribution.map((item, i) => <FitCard key={i} item={item} field="match" label="Fit" />)}
      </section>
    </>
  );
}

// ---- Analytics ----

function Analytics({ stats }) {
  return (
    <>
      <section className="section">
        <div className="two-col">
          <div className="chart-panel">
            <div className="chart-panel-title">Full Technology Landscape</div>
            <BarChart data={stats.technologies.slice(0, 15)} max={stats.technologies[0]?.[1]} />
          </div>
          <div className="chart-panel">
            <div className="chart-panel-title">Full Industry Coverage</div>
            <BarChart data={stats.industries} max={stats.industries[0]?.[1]} alt />
          </div>
        </div>
      </section>
    </>
  );
}

// ---- Modal ----

function Modal({ data, onClose, addToCart, isInCart }) {
  const techs = (data.technologies || "").split(", ").filter(Boolean);
  const inCart = isInCart && isInCart(data.id);
  const sections = [
    ["Client", data.client],
    ["Challenge", data.challenge],
    ["Solution", data.solution],
    ["Results", data.results],
  ].filter(([, v]) => v);

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
        <div className="modal-header">
          <button className="modal-close" onClick={onClose} aria-label="Close modal">&times;</button>
          <div className="card-meta" style={{ marginBottom: 8 }}>
            {data.industry && <span className="badge badge-industry">{data.industry}</span>}
            {techs.slice(0, 3).map((t, i) => <span key={i} className="badge badge-tech">{t}</span>)}
          </div>
          <div className="modal-title">{data.title}</div>
        </div>
        <div className="modal-body">
          {sections.map(([title, text]) => (
            <div className="modal-section" key={title}>
              <div className="modal-section-title">{title}</div>
              <div className="modal-section-text">{text}</div>
            </div>
          ))}
          {techs.length > 0 && (
            <div className="modal-section">
              <div className="modal-section-title">Technologies</div>
              <div className="tech-list" style={{ gap: 6 }}>
                {techs.map((t, i) => <span key={i} className="badge badge-tech">{t}</span>)}
              </div>
            </div>
          )}
          <div className="modal-section" style={{ display: "flex", gap: 12, alignItems: "center" }}>
            {data.url && (
              <a href={data.url} target="_blank" rel="noopener noreferrer" className="card-link" style={{ fontSize: 13 }}>
                View on phData.io <ExternalIcon />
              </a>
            )}
            {addToCart && (
              <button
                className={`cart-add-modal-btn ${inCart ? "in-cart" : ""}`}
                onClick={() => { if (!inCart) addToCart(data); }}
              >
                {inCart ? <><CheckIcon /> In Cart</> : <><CartIcon size={14} /> Add to Cart</>}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Prospect Map ----

const PROSPECT_TYPE_COLORS = {
  "Pharma / CDMO": "#e06c75",
  "Pharma": "#e5c07b",
  "Medical Device": "#61afef",
  "Diagnostics": "#56b6c2",
  "Diagnostics / Biotech": "#82e0aa",
  "Diagnostics / Life Sciences": "#3ba3b8",
  "Life Sciences Tools": "#c678dd",
};

const TAG_COLORS = {
  "GenAI": "#c678dd",
  "ML": "#61afef",
  "NLP": "#56b6c2",
  "Data Platform": "#3ba3b8",
  "Cloud Migration": "#98c379",
  "Analytics": "#e5c07b",
  "Snowflake": "#85c1e9",
  "IoT": "#d19a66",
  "Genomics": "#bb8fce",
  "Revenue Cycle": "#e06c75",
  "Real-time": "#ff6b6b",
  "Federated Learning": "#f1948a",
  "Automation": "#82e0aa",
  "Telehealth": "#4ecdc4",
  "Dashboards": "#aed6f1",
  "Computer Vision": "#d7bde2",
  "Data Pipeline": "#a3e4d7",
  "Data Lake": "#f0b27a",
};

function ProspectMap() {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef([]);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState("All");
  const [countyFilter, setCountyFilter] = useState("All");
  const [tagFilter, setTagFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [detailPulse, setDetailPulse] = useState(false);

  useEffect(() => {
    fetch("/api/prospects").then(r => r.json()).then(setData);
  }, []);

  // Initialize map
  useEffect(() => {
    if (!data || !mapRef.current || mapInstance.current) return;

    const map = L.map(mapRef.current, {
      zoomControl: false,
      attributionControl: false,
    }).setView([39.75, -105.00], 8);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Dark tile layer
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
    }).addTo(map);

    mapInstance.current = map;

    return () => { map.remove(); mapInstance.current = null; };
  }, [data]);

  // Update markers when filters change
  useEffect(() => {
    if (!data || !mapInstance.current) return;
    const map = mapInstance.current;

    // Clear old markers
    markersRef.current.forEach(m => map.removeLayer(m));
    markersRef.current = [];

    const filtered = data.prospects.filter(p => {
      if (filter !== "All" && p.type !== filter) return false;
      if (countyFilter !== "All" && p.county !== countyFilter) return false;
      if (tagFilter !== "All" && !p.tags.includes(tagFilter)) return false;
      if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });

    filtered.forEach(p => {
      const color = PROSPECT_TYPE_COLORS[p.type] || "#888";
      const size = Math.max(12, 8 + p.projects * 3);
      const icon = L.divIcon({
        className: "",
        html: `<div style="
          width:${size}px;height:${size}px;border-radius:50%;
          background:${color};border:2px solid rgba(255,255,255,0.8);
          box-shadow:0 0 12px ${color}80, 0 2px 8px rgba(0,0,0,0.4);
          cursor:pointer;transition:transform 0.15s;
        " onmouseover="this.style.transform='scale(1.3)'" onmouseout="this.style.transform='scale(1)'"></div>`,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
      });

      const marker = L.marker([p.lat, p.lng], { icon }).addTo(map);
      marker.on("click", () => {
        setSelected(p);
        setDetailPulse(true);
        setTimeout(() => setDetailPulse(false), 600);
        map.flyTo([p.lat, p.lng], 13, { duration: 0.8 });
      });
      const tipHtml = p.logo
        ? `<div style="display:flex;align-items:center;gap:6px"><img src="/static/logos/${p.logo}.png" style="width:16px;height:16px;border-radius:3px;background:#fff;object-fit:contain" /><span>${p.name}</span></div>`
        : p.name;
      marker.bindTooltip(tipHtml, {
        className: "prospect-tooltip-leaf",
        direction: "top",
        offset: [0, -size / 2 - 4],
      });
      markersRef.current.push(marker);
    });
  }, [data, filter, countyFilter, tagFilter, searchQuery]);

  if (!data) return <div className="prospect-map-wrap"><div style={{ display: "grid", placeItems: "center", height: "100%", color: "rgba(255,255,255,0.4)" }}><div className="loading"><div className="spinner" />Loading prospects...</div></div></div>;

  const types = ["All", ...new Set(data.prospects.map(p => p.type))];
  const allTags = ["All", ...new Set(data.prospects.flatMap(p => p.tags)).values()].sort();
  const totalProjects = data.stats.total_projects;

  const filtered = data.prospects.filter(p => {
    if (filter !== "All" && p.type !== filter) return false;
    if (countyFilter !== "All" && p.county !== countyFilter) return false;
    if (tagFilter !== "All" && !p.tags.includes(tagFilter)) return false;
    if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });
  const filteredProjects = filtered.reduce((s, p) => s + p.projects, 0);

  const handleBackToAll = () => {
    setSelected(null);
    setSearchQuery("");
    setFilter("All");
    setCountyFilter("All");
    setTagFilter("All");
    mapInstance.current?.flyTo([39.75, -105.00], 8, { duration: 0.8 });
  };

  return (
    <div className="prospect-map-wrap">
      {/* Left panel — dense controls */}
      <div className="prospect-panel">
        <div className="prospect-section">
          <div className="prospect-stats-row">
            <div className="prospect-stat">
              <div className="prospect-stat-num">{filtered.length}</div>
              <div className="prospect-stat-label">Organizations</div>
            </div>
            <div className="prospect-stat">
              <div className="prospect-stat-num">{filteredProjects}</div>
              <div className="prospect-stat-label">Projects</div>
            </div>
          </div>
        </div>

        <div className="prospect-section">
          <div className="prospect-filter-label">Region</div>
          <div className="prospect-pill-row">
            {["All", ...Object.keys(data?.stats?.by_county || {})].map(c => (
              <button key={c} className={`prospect-pill ${countyFilter === c ? "active" : ""}`} onClick={() => setCountyFilter(c)}>{c}</button>
            ))}
          </div>
        </div>

        <div className="prospect-section">
          <div className="prospect-filter-label">Type</div>
          <select className="prospect-select" value={filter} onChange={e => setFilter(e.target.value)}>
            {types.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        <div className="prospect-section">
          <div className="prospect-filter-label">Capability</div>
          <select className="prospect-select" value={tagFilter} onChange={e => setTagFilter(e.target.value)}>
            {allTags.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        <div className="prospect-section">
          <div className="prospect-section-title">Legend</div>
          <div className="prospect-legend">
            {Object.entries(PROSPECT_TYPE_COLORS).map(([type, color]) => (
              <div key={type} className={`prospect-legend-item ${filter !== "All" && filter !== type ? "dimmed" : ""}`}
                onClick={() => setFilter(filter === type ? "All" : type)}>
                <span className="prospect-legend-dot" style={{ background: color }} />
                <span>{type}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="prospect-section" style={{ flex: 1, minHeight: 0 }}>
          <div className="prospect-section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Organizations</span>
            {(selected || filter !== "All" || countyFilter !== "All" || tagFilter !== "All" || searchQuery) && (
              <button className="prospect-back-btn" onClick={handleBackToAll}>Reset All</button>
            )}
          </div>
          <input
            type="text"
            className="prospect-search-input"
            placeholder="Search companies..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            aria-label="Search prospect companies"
          />
          <div className="prospect-list">
            {filtered.map(p => (
              <div key={p.id} className={`prospect-list-item ${selected?.id === p.id ? "active" : ""}`}
                onClick={() => {
                  setSelected(p);
                  setDetailPulse(true);
                  setTimeout(() => setDetailPulse(false), 600);
                  mapInstance.current?.flyTo([p.lat, p.lng], 13, { duration: 0.8 });
                }}>
                <div className="prospect-logo-container">
                  {p.logo ? (
                    <img src={`/static/logos/${p.logo}.png`} alt="" className="prospect-logo-sm"
                      onError={e => { e.target.style.display = "none"; e.target.nextSibling && (e.target.nextSibling.style.display = "flex"); }}
                    />
                  ) : null}
                  {!p.logo && (
                    <span className="prospect-monogram" style={{ background: PROSPECT_TYPE_COLORS[p.type] || "#888" }}>
                      {p.name.split(" ").map(w => w[0]).join("").slice(0, 2)}
                    </span>
                  )}
                  <span className="prospect-type-indicator" style={{ background: PROSPECT_TYPE_COLORS[p.type] || "#888" }} />
                </div>
                <div className="prospect-list-text">
                  <div className="prospect-list-name">{p.name}</div>
                  <div className="prospect-list-meta">{p.type} | {p.projects} projects</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Map — focal point */}
      <div className="prospect-map-container">
        <div ref={mapRef} style={{ width: "100%", height: "100%" }} />
      </div>

      {/* Right panel — detail */}
      <div className={`prospect-panel prospect-panel-right ${detailPulse ? "prospect-panel-pulse" : ""}`}>
        {selected ? (
          <div className="prospect-detail-card">
            <div className="prospect-detail-header">
              <div className="prospect-logo-wrap">
                {selected.logo ? (
                  <img src={`/static/logos/${selected.logo}.png`} alt={selected.name} className="prospect-logo-lg" />
                ) : (
                  <span className="prospect-monogram-lg" style={{ background: PROSPECT_TYPE_COLORS[selected.type] || "#888" }}>
                    {selected.name.split(" ").map(w => w[0]).join("").slice(0, 2)}
                  </span>
                )}
              </div>
              <div className="prospect-detail-header-text">
                <div className="prospect-type-badge">
                  <span className="prospect-type-dot" style={{ background: PROSPECT_TYPE_COLORS[selected.type] || "#888" }} />
                  {selected.type}
                </div>
                <div className="prospect-detail-name">{selected.name}</div>
                <div className="prospect-detail-addr">{selected.address}</div>
              </div>
            </div>

            <div className="prospect-detail-stats">
              <div className="prospect-detail-stat">
                <div className="prospect-detail-stat-num">{selected.projects}</div>
                <div className="prospect-detail-stat-label">Projects</div>
              </div>
              <div className="prospect-detail-stat">
                <div className="prospect-detail-stat-num">{selected.revenue}</div>
                <div className="prospect-detail-stat-label">Revenue</div>
              </div>
              <div className="prospect-detail-stat">
                <div className="prospect-detail-stat-num">{selected.employees}</div>
                <div className="prospect-detail-stat-label">Employees</div>
              </div>
            </div>

            <div className="prospect-detail-section">
              <div className="prospect-detail-heading">Opportunity</div>
              <div className="prospect-detail-text">{selected.opportunity}</div>
            </div>

            <div className="prospect-detail-section">
              <div className="prospect-detail-heading">Why phData</div>
              <div className="prospect-detail-text">{selected.rationale}</div>
            </div>

            <div className="prospect-detail-section">
              <div className="prospect-detail-heading">Capabilities</div>
              <div className="prospect-tag-list">
                {selected.tags.map(t => (
                  <span key={t} className="prospect-tag" style={{ background: (TAG_COLORS[t] || "#888") + "22", color: TAG_COLORS[t] || "#888", borderColor: (TAG_COLORS[t] || "#888") + "44" }}>
                    {t}
                  </span>
                ))}
              </div>
            </div>

            <div className="prospect-detail-section">
              <div className="prospect-detail-heading">Region</div>
              <div className="prospect-detail-text">{selected.county} Area</div>
            </div>

            {selected.url && (
              <div className="prospect-detail-section">
                <a href={selected.url} target="_blank" rel="noopener noreferrer" className="prospect-site-link">
                  Visit Website <ExternalIcon />
                </a>
              </div>
            )}
          </div>
        ) : (
          <div className="prospect-empty-state">
            <div className="prospect-empty-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
            </div>
            <div className="prospect-empty-title">Select an organization</div>
            <div className="prospect-empty-sub">Click a marker on the map or choose from the list to view details, opportunities, and phData alignment</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Projector (t-SNE) ----

// Minimal t-SNE implementation (van der Maaten, 2008)
function tsne(X, opts = {}) {
  const { dim = 2, perplexity = 30, epsilon = 10, maxIter = 500, onIter } = opts;
  const n = X.length;

  function pdist2(data) {
    const D = new Float64Array(n * n);
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let s = 0;
        for (let k = 0; k < data[0].length; k++) {
          const diff = (data[i][k] || 0) - (data[j][k] || 0);
          s += diff * diff;
        }
        D[i * n + j] = s;
        D[j * n + i] = s;
      }
    }
    return D;
  }

  function computeP(D) {
    const P = new Float64Array(n * n);
    const logPerp = Math.log(perplexity);
    for (let i = 0; i < n; i++) {
      let lo = 1e-20, hi = 1e4, mid = 1;
      for (let iter = 0; iter < 50; iter++) {
        let sumP = 0;
        for (let j = 0; j < n; j++) {
          if (j === i) { P[i * n + j] = 0; continue; }
          P[i * n + j] = Math.exp(-D[i * n + j] * mid);
          sumP += P[i * n + j];
        }
        if (sumP === 0) sumP = 1e-10;
        let H = 0;
        for (let j = 0; j < n; j++) {
          if (j === i) continue;
          P[i * n + j] /= sumP;
          if (P[i * n + j] > 1e-10) H -= P[i * n + j] * Math.log(P[i * n + j]);
        }
        if (Math.abs(H - logPerp) < 1e-4) break;
        if (H > logPerp) lo = mid; else hi = mid;
        mid = (lo + hi) / 2;
      }
    }
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const v = (P[i * n + j] + P[j * n + i]) / (2 * n);
        P[i * n + j] = v;
        P[j * n + i] = v;
      }
    }
    return P;
  }

  const D = pdist2(X);
  const P = computeP(D);

  const Y = Array.from({ length: n }, () =>
    Array.from({ length: dim }, () => (Math.random() - 0.5) * 0.01)
  );
  const Yprev = Y.map(row => [...row]);
  const gains = Array.from({ length: n }, () => Array(dim).fill(1));

  let stopped = false;
  const stop = () => { stopped = true; };

  function step(iter) {
    if (stopped) return Y;
    const Qnum = new Float64Array(n * n);
    let sumQ = 0;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let s = 0;
        for (let k = 0; k < dim; k++) {
          const diff = Y[i][k] - Y[j][k];
          s += diff * diff;
        }
        const v = 1 / (1 + s);
        Qnum[i * n + j] = v;
        Qnum[j * n + i] = v;
        sumQ += 2 * v;
      }
    }
    if (sumQ === 0) sumQ = 1e-10;

    const mult = iter < 100 ? 4 : 1;
    const mom = iter < 250 ? 0.5 : 0.8;
    for (let i = 0; i < n; i++) {
      for (let k = 0; k < dim; k++) {
        let grad = 0;
        for (let j = 0; j < n; j++) {
          if (j === i) continue;
          const pq = mult * P[i * n + j] - Qnum[i * n + j] / sumQ;
          grad += 4 * pq * Qnum[i * n + j] * (Y[i][k] - Y[j][k]);
        }
        const dir = Math.sign(grad) !== Math.sign(Y[i][k] - Yprev[i][k]);
        gains[i][k] = dir ? gains[i][k] + 0.2 : gains[i][k] * 0.8;
        if (gains[i][k] < 0.01) gains[i][k] = 0.01;
        const prev = Y[i][k];
        Y[i][k] = Y[i][k] - epsilon * gains[i][k] * grad + mom * (Y[i][k] - Yprev[i][k]);
        Yprev[i][k] = prev;
      }
    }

    for (let k = 0; k < dim; k++) {
      let mean = 0;
      for (let i = 0; i < n; i++) mean += Y[i][k];
      mean /= n;
      for (let i = 0; i < n; i++) Y[i][k] -= mean;
    }

    if (onIter) onIter(iter, Y);
    return Y;
  }

  return { step, stop, Y, maxIter };
}

// K-means clustering on 2D points
function kmeans(points, k, maxIter = 50) {
  const n = points.length;
  if (n <= k) return points.map((_, i) => i);

  // Initialize centroids with k-means++
  const centroids = [];
  centroids.push([points[Math.floor(Math.random() * n)].x, points[Math.floor(Math.random() * n)].y]);
  for (let c = 1; c < k; c++) {
    const dists = points.map(p => {
      let minD = Infinity;
      centroids.forEach(ct => {
        const dx = p.x - ct[0], dy = p.y - ct[1];
        minD = Math.min(minD, dx * dx + dy * dy);
      });
      return minD;
    });
    const totalD = dists.reduce((a, b) => a + b, 0);
    let r = Math.random() * totalD, acc = 0;
    for (let i = 0; i < n; i++) {
      acc += dists[i];
      if (acc >= r) { centroids.push([points[i].x, points[i].y]); break; }
    }
    if (centroids.length <= c) centroids.push([points[Math.floor(Math.random() * n)].x, points[Math.floor(Math.random() * n)].y]);
  }

  let assignments = new Array(n).fill(0);
  for (let iter = 0; iter < maxIter; iter++) {
    // Assign
    let changed = false;
    for (let i = 0; i < n; i++) {
      let bestC = 0, bestD = Infinity;
      for (let c = 0; c < k; c++) {
        const dx = points[i].x - centroids[c][0], dy = points[i].y - centroids[c][1];
        const d = dx * dx + dy * dy;
        if (d < bestD) { bestD = d; bestC = c; }
      }
      if (assignments[i] !== bestC) changed = true;
      assignments[i] = bestC;
    }
    if (!changed) break;

    // Update centroids
    for (let c = 0; c < k; c++) {
      let sx = 0, sy = 0, count = 0;
      for (let i = 0; i < n; i++) {
        if (assignments[i] === c) { sx += points[i].x; sy += points[i].y; count++; }
      }
      if (count > 0) { centroids[c][0] = sx / count; centroids[c][1] = sy / count; }
    }
  }
  return assignments;
}

// Convex hull (Andrew's monotone chain)
function convexHull(pts) {
  if (pts.length < 3) return pts;
  const sorted = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (O, A, B) => (A[0] - O[0]) * (B[1] - O[1]) - (A[1] - O[1]) * (B[0] - O[0]);
  const lower = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  upper.pop();
  lower.pop();
  return lower.concat(upper);
}

// Expand hull outward by a padding amount
function expandHull(hull, pad) {
  if (hull.length < 3) return hull;
  // Compute centroid
  let cx = 0, cy = 0;
  hull.forEach(p => { cx += p[0]; cy += p[1]; });
  cx /= hull.length; cy /= hull.length;
  return hull.map(p => {
    const dx = p[0] - cx, dy = p[1] - cy;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    return [p[0] + (dx / len) * pad, p[1] + (dy / len) * pad];
  });
}

// Cluster colors (distinct from industry colors)
const CLUSTER_COLORS = [
  "#3ba3b8", "#e06c75", "#98c379", "#d19a66", "#c678dd",
  "#61afef", "#e5c07b", "#56b6c2", "#be5046", "#ff6b6b",
  "#4ecdc4", "#45b7d1", "#f7dc6f", "#bb8fce", "#82e0aa",
];

// Industry color palette
const INDUSTRY_COLORS = [
  "#3ba3b8", "#e06c75", "#98c379", "#d19a66", "#c678dd",
  "#61afef", "#e5c07b", "#56b6c2", "#be5046", "#abb2bf",
  "#ff6b6b", "#4ecdc4", "#45b7d1", "#f7dc6f", "#bb8fce",
  "#85c1e9", "#f0b27a", "#82e0aa", "#f1948a", "#aed6f1",
  "#d7bde2", "#a3e4d7",
];

function Projector() {
  const canvasRef = useRef(null);
  const [data, setData] = useState(null);
  const [points, setPoints] = useState(null);
  const [running, setRunning] = useState(false);
  const [iteration, setIteration] = useState(0);
  const [perplexity, setPerplexity] = useState(15);
  const [learningRate, setLearningRate] = useState(10);
  const [maxIter, setMaxIter] = useState(500);
  const [numClusters, setNumClusters] = useState(6);
  const [hovered, setHovered] = useState(null);
  const [selected, setSelected] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [industries, setIndustries] = useState({});
  const [industryColors, setIndustryColors] = useState({});
  const [clusters, setClusters] = useState(null); // { assignments: [], labels: {}, k: N }
  const [clusterStatus, setClusterStatus] = useState(""); // "", "clustering", "naming", "done"
  const [camera, setCamera] = useState({ x: 0, y: 0, zoom: 1 });
  const [embeddingMode, setEmbeddingMode] = useState("full"); // "full" | "titles"
  const [loadingVectors, setLoadingVectors] = useState(false);
  const dragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, cx: 0, cy: 0 });
  const tsneRef = useRef(null);
  const animRef = useRef(null);
  const tooltipPos = useRef({ x: 0, y: 0 });

  // Load vectors — re-fetch when embedding mode changes
  useEffect(() => {
    setLoadingVectors(true);
    setPoints(null);
    setClusters(null);
    setClusterStatus("");
    setIteration(0);
    setRunning(false);
    if (animRef.current) cancelAnimationFrame(animRef.current);
    fetch(`/api/vectors?mode=${embeddingMode}`).then(r => r.json()).then(d => {
      setData(d);
      const indMap = {};
      const colorMap = {};
      let ci = 0;
      d.documents.forEach(doc => {
        const ind = doc.industry || "Unknown";
        if (!(ind in indMap)) {
          indMap[ind] = true;
          colorMap[ind] = INDUSTRY_COLORS[ci % INDUSTRY_COLORS.length];
          ci++;
        }
      });
      setIndustries(indMap);
      setIndustryColors(colorMap);
      setLoadingVectors(false);
    });
  }, [embeddingMode]);

  // Run clustering + naming after t-SNE finishes
  const runClustering = useCallback(async (pts, k) => {
    if (!pts || pts.length < 3) return;
    setClusterStatus("clustering");
    setClusters(null);

    const assignments = kmeans(pts, k);

    // Group titles by cluster
    const clusterGroups = {};
    assignments.forEach((cid, i) => {
      if (!clusterGroups[cid]) clusterGroups[cid] = [];
      clusterGroups[cid].push(pts[i].title);
    });

    // Initialize with placeholder labels, show hulls immediately
    const placeholderLabels = {};
    Object.keys(clusterGroups).forEach(id => { placeholderLabels[id] = `Naming...`; });
    setClusters({ assignments, labels: placeholderLabels, k });
    setClusterStatus("naming");

    // Name each cluster one at a time via claude -p, streaming results in
    const clusterIds = Object.entries(clusterGroups);
    let named = 0;
    for (const [id, titles] of clusterIds) {
      try {
        const resp = await fetch("/api/name-cluster", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: +id, titles }),
        });
        const data = await resp.json();
        named++;
        setClusterStatus(`naming ${named}/${clusterIds.length}`);
        setClusters(prev => ({
          ...prev,
          labels: { ...prev.labels, [String(data.id)]: data.label },
        }));
      } catch (e) {
        named++;
        setClusters(prev => ({
          ...prev,
          labels: { ...prev.labels, [id]: `Cluster ${+id + 1}` },
        }));
      }
    }
    setClusterStatus("done");
  }, []);

  // Run t-SNE
  const runTSNE = useCallback(() => {
    if (!data) return;
    if (tsneRef.current) tsneRef.current.stop();
    setClusters(null);
    setClusterStatus("");

    const activeInds = new Set(Object.entries(industries).filter(([,v]) => v).map(([k]) => k));
    const filtered = data.documents.filter(d => activeInds.has(d.industry || "Unknown"));
    if (filtered.length < 3) return;

    const vectors = filtered.map(d => d.vector);
    const perp = Math.min(perplexity, Math.floor((filtered.length - 1) / 3));

    let finalPoints = null;
    const runner = tsne(vectors, {
      perplexity: perp,
      epsilon: learningRate,
      maxIter,
      onIter: (iter, Y) => {
        setIteration(iter + 1);
        finalPoints = filtered.map((doc, i) => ({
          ...doc,
          x: Y[i][0],
          y: Y[i][1],
        }));
        setPoints(finalPoints);
      },
    });
    tsneRef.current = runner;
    setRunning(true);
    setIteration(0);

    let iter = 0;
    function tick() {
      if (iter >= maxIter) {
        setRunning(false);
        // Auto-cluster when t-SNE finishes
        if (finalPoints) runClustering(finalPoints, numClusters);
        return;
      }
      runner.step(iter);
      iter++;
      animRef.current = requestAnimationFrame(tick);
    }
    animRef.current = requestAnimationFrame(tick);
  }, [data, industries, perplexity, learningRate, maxIter, numClusters, runClustering]);

  // Auto-run on data load
  useEffect(() => {
    if (data && Object.keys(industries).length > 0) {
      runTSNE();
    }
    return () => {
      if (tsneRef.current) tsneRef.current.stop();
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [data]);

  // Draw canvas
  useEffect(() => {
    if (!points || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = rect.height;

    ctx.fillStyle = "#0c1118";
    ctx.fillRect(0, 0, W, H);

    // Subtle grid
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    for (let i = 0; i < W; i += 40) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, H); ctx.stroke(); }
    for (let i = 0; i < H; i += 40) { ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(W, i); ctx.stroke(); }

    if (points.length === 0) return;

    // Scale to fit with camera transform (pan + zoom)
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    points.forEach(p => { minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); });
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const pad = 60;
    const z = camera.zoom;
    const cx = W / 2 + camera.x;
    const cy = H / 2 + camera.y;
    const sx = (p) => cx + (((p.x - minX) / rangeX - 0.5) * (W - 2 * pad)) * z;
    const sy = (p) => cy + (((p.y - minY) / rangeY - 0.5) * (H - 2 * pad)) * z;

    const searchLC = searchQuery.toLowerCase();
    const matchesSearch = (p) => !searchLC || p.title.toLowerCase().includes(searchLC) || (p.technologies || "").toLowerCase().includes(searchLC);

    // Draw convex hulls if clusters exist
    if (clusters && clusters.assignments) {
      const clusterPoints = {};
      points.forEach((p, i) => {
        const cid = clusters.assignments[i];
        if (cid === undefined) return;
        if (!clusterPoints[cid]) clusterPoints[cid] = [];
        clusterPoints[cid].push([sx(p), sy(p)]);
      });

      Object.entries(clusterPoints).forEach(([cid, cpts]) => {
        if (cpts.length < 3) return;
        const hull = convexHull(cpts);
        if (hull.length < 3) return;
        const expanded = expandHull(hull, 18);
        const color = CLUSTER_COLORS[cid % CLUSTER_COLORS.length];

        // Fill hull
        ctx.beginPath();
        ctx.moveTo(expanded[0][0], expanded[0][1]);
        for (let i = 1; i < expanded.length; i++) ctx.lineTo(expanded[i][0], expanded[i][1]);
        ctx.closePath();
        ctx.fillStyle = color.replace(")", ",0.06)").replace("rgb", "rgba").replace("#", "");
        // Convert hex to rgba fill
        const r = parseInt(color.slice(1,3), 16), g = parseInt(color.slice(3,5), 16), b = parseInt(color.slice(5,7), 16);
        ctx.fillStyle = `rgba(${r},${g},${b},0.07)`;
        ctx.fill();

        // Stroke hull
        ctx.beginPath();
        ctx.moveTo(expanded[0][0], expanded[0][1]);
        for (let i = 1; i < expanded.length; i++) ctx.lineTo(expanded[i][0], expanded[i][1]);
        ctx.closePath();
        ctx.strokeStyle = `rgba(${r},${g},${b},0.35)`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Label
        const label = clusters.labels?.[String(cid)] || `Cluster ${+cid + 1}`;
        // Position label at top of hull
        let topPt = expanded[0];
        expanded.forEach(ep => { if (ep[1] < topPt[1]) topPt = ep; });
        const lx = topPt[0];
        const ly = topPt[1] - 10;

        ctx.font = "600 11px 'Inter', sans-serif";
        const tm = ctx.measureText(label);
        const lpad = 6;

        // Label background
        ctx.fillStyle = `rgba(${r},${g},${b},0.15)`;
        ctx.beginPath();
        const rx = lx - tm.width / 2 - lpad;
        const ry = ly - 12;
        const rw = tm.width + lpad * 2;
        const rh = 18;
        const br = 4;
        ctx.moveTo(rx + br, ry);
        ctx.lineTo(rx + rw - br, ry);
        ctx.quadraticCurveTo(rx + rw, ry, rx + rw, ry + br);
        ctx.lineTo(rx + rw, ry + rh - br);
        ctx.quadraticCurveTo(rx + rw, ry + rh, rx + rw - br, ry + rh);
        ctx.lineTo(rx + br, ry + rh);
        ctx.quadraticCurveTo(rx, ry + rh, rx, ry + rh - br);
        ctx.lineTo(rx, ry + br);
        ctx.quadraticCurveTo(rx, ry, rx + br, ry);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = `rgba(${r},${g},${b},0.4)`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label text
        ctx.fillStyle = `rgba(${r},${g},${b},0.9)`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, lx, ly - 3);
        ctx.textAlign = "start";
        ctx.textBaseline = "alphabetic";
      });
    }

    // Draw points
    points.forEach(p => {
      const px = sx(p);
      const py = sy(p);
      const isMatch = matchesSearch(p);
      const isHov = hovered && hovered.id === p.id;
      const isSel = selected && selected.id === p.id;
      const color = industryColors[p.industry] || "#888";
      const alpha = searchLC && !isMatch ? 0.1 : 1;
      const radius = isSel ? 8 : isHov ? 7 : 5;

      if (isMatch && !isHov && !isSel) {
        ctx.beginPath();
        ctx.arc(px, py, radius + 4, 0, Math.PI * 2);
        const cr = parseInt(color.slice(1,3), 16), cg = parseInt(color.slice(3,5), 16), cb = parseInt(color.slice(5,7), 16);
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${alpha * 0.12})`;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fillStyle = alpha < 1 ? `rgba(60,60,60,${alpha})` : color;
      ctx.fill();

      if (isSel || isHov) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });

    // Store mapping for hit detection
    canvas._pointMap = points.map(p => ({ ...p, px: sx(p), py: sy(p) }));
  }, [points, hovered, selected, searchQuery, industryColors, clusters, camera]);

  // Mouse interaction — pan/drag + hover
  const handleMouseDown = useCallback((e) => {
    dragging.current = true;
    dragStart.current = { x: e.clientX, y: e.clientY, cx: camera.x, cy: camera.y };
  }, [camera]);

  const handleMouseMove = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    tooltipPos.current = { x: mx, y: my };

    if (dragging.current) {
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      setCamera(prev => ({ ...prev, x: dragStart.current.cx + dx, y: dragStart.current.cy + dy }));
      return;
    }

    if (!canvas._pointMap) return;
    let closest = null, closestDist = 20;
    canvas._pointMap.forEach(p => {
      const ddx = p.px - mx, ddy = p.py - my;
      const dist = Math.sqrt(ddx * ddx + ddy * ddy);
      if (dist < closestDist) { closest = p; closestDist = dist; }
    });
    setHovered(closest);
  }, []);

  const handleMouseUp = useCallback(() => {
    dragging.current = false;
  }, []);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setCamera(prev => ({ ...prev, zoom: Math.max(0.2, Math.min(10, prev.zoom * delta)) }));
  }, []);

  const handleClick = useCallback(() => {
    if (hovered && !dragging.current) setSelected(hovered);
  }, [hovered]);

  if (!data) return <div className="projector"><div style={{ gridColumn: "1 / -1", display: "grid", placeItems: "center", color: "rgba(255,255,255,0.4)" }}><div className="loading"><div className="spinner" />Loading vectors...</div></div></div>;

  const activeCount = Object.values(industries).filter(Boolean).length;
  const filteredCount = points ? points.length : data.documents.length;

  return (
    <div className="projector">
      {/* Left panel — Controls */}
      <div className="projector-panel">
        <div className="projector-panel-title">Controls</div>

        <div className="projector-section">
          <div className="projector-label">Embeddings</div>
          <div className="projector-mode-toggle">
            <button
              className={`projector-mode-btn ${embeddingMode === "full" ? "active" : ""}`}
              onClick={() => setEmbeddingMode("full")}
              disabled={loadingVectors}
            >Full Content</button>
            <button
              className={`projector-mode-btn ${embeddingMode === "titles" ? "active" : ""}`}
              onClick={() => setEmbeddingMode("titles")}
              disabled={loadingVectors}
            >Titles Only</button>
          </div>
          <div className="projector-label" style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", marginTop: 4 }}>
            {loadingVectors ? "Loading vectors..." : embeddingMode === "full" ? `${data?.vocab_size || 0} dimensions — deep similarity` : `${data?.vocab_size || 0} dimensions — topic clustering`}
          </div>
        </div>

        <div className="projector-section">
          <div className="projector-label">Iteration</div>
          <div className="projector-iter-display">{iteration}</div>
          <div className="projector-label" style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>of {maxIter}</div>
        </div>

        <div className="projector-section">
          <div className="projector-label">Perplexity: <span className="projector-value">{perplexity}</span></div>
          <input type="range" className="projector-slider" min="2" max="50" value={perplexity} onChange={e => setPerplexity(+e.target.value)} />
        </div>

        <div className="projector-section">
          <div className="projector-label">Learning Rate: <span className="projector-value">{learningRate}</span></div>
          <input type="range" className="projector-slider" min="1" max="100" value={learningRate} onChange={e => setLearningRate(+e.target.value)} />
        </div>

        <div className="projector-section">
          <div className="projector-label">Max Iterations: <span className="projector-value">{maxIter}</span></div>
          <input type="range" className="projector-slider" min="100" max="1500" step="100" value={maxIter} onChange={e => setMaxIter(+e.target.value)} />
        </div>

        <div className="projector-section">
          <div className="projector-label">Clusters (k): <span className="projector-value">{numClusters}</span></div>
          <input type="range" className="projector-slider" min="2" max="12" value={numClusters} onChange={e => setNumClusters(+e.target.value)} />
        </div>

        <button className="projector-btn" onClick={runTSNE} disabled={running || loadingVectors}>
          {loadingVectors ? "Loading vectors..." : running ? "Running..." : "Run t-SNE"}
        </button>

        <div style={{ display: "flex", gap: 6 }}>
          <button className="projector-btn projector-btn-outline" style={{ flex: 1 }} onClick={() => {
            if (tsneRef.current) tsneRef.current.stop();
            if (animRef.current) cancelAnimationFrame(animRef.current);
            setRunning(false);
          }} disabled={!running}>
            Stop
          </button>
          <button className="projector-btn projector-btn-outline" style={{ flex: 1 }} onClick={() => {
            if (points) runClustering(points, numClusters);
          }} disabled={running || !points || clusterStatus.startsWith("naming")}>
            Re-cluster
          </button>
        </div>

        {clusterStatus && (
          <div className="projector-section">
            <div className="projector-label" style={{ fontSize: 11 }}>
              {clusterStatus === "clustering" && "Computing k-means..."}
              {clusterStatus.startsWith("naming") && `Naming via Claude... (${clusterStatus.replace("naming ", "").replace("naming", "0/" + numClusters)})`}
              {clusterStatus === "done" && "Clusters labeled"}
            </div>
            {clusterStatus.startsWith("naming") && (() => {
              const parts = clusterStatus.replace("naming ", "").split("/");
              const done = parseInt(parts[0]) || 0;
              const total = parseInt(parts[1]) || numClusters;
              const pct = total > 0 ? (done / total) * 100 : 0;
              return (
                <div style={{ width: "100%", height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden", marginTop: 4 }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: "var(--teal-400)", borderRadius: 2, transition: "width 0.3s ease" }} />
                </div>
              );
            })()}
          </div>
        )}

        <div className="projector-section" style={{ marginTop: 4 }}>
          <div className="projector-panel-title">Filter by Industry</div>
          <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
            <button className="projector-btn projector-btn-outline" style={{ padding: "3px 8px", fontSize: 10 }}
              onClick={() => setIndustries(prev => { const n = {}; Object.keys(prev).forEach(k => n[k] = true); return n; })}>All</button>
            <button className="projector-btn projector-btn-outline" style={{ padding: "3px 8px", fontSize: 10 }}
              onClick={() => setIndustries(prev => { const n = {}; Object.keys(prev).forEach(k => n[k] = false); return n; })}>None</button>
          </div>
          <div className="projector-filter-list">
            {Object.keys(industries).sort().map(ind => (
              <label className="projector-filter-item" key={ind}>
                <input type="checkbox" checked={!!industries[ind]}
                  onChange={e => setIndustries(prev => ({ ...prev, [ind]: e.target.checked }))} />
                <span className="projector-filter-dot" style={{ background: industryColors[ind] }} />
                {ind}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Center — Canvas */}
      <div className="projector-canvas-wrap">
        <canvas ref={canvasRef} className="projector-canvas"
          onMouseDown={handleMouseDown} onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}
          onWheel={handleWheel} onClick={handleClick} />
        <div className="projector-zoom-controls">
          <button className="projector-zoom-btn" onClick={() => setCamera(prev => ({ ...prev, zoom: Math.min(10, prev.zoom * 1.3) }))}>+</button>
          <button className="projector-zoom-btn" onClick={() => setCamera(prev => ({ ...prev, zoom: Math.max(0.2, prev.zoom / 1.3) }))}>-</button>
          <button className="projector-zoom-btn projector-zoom-fit" onClick={() => setCamera({ x: 0, y: 0, zoom: 1 })}>Fit</button>
        </div>
        <div className="projector-status">
          {filteredCount} points | {activeCount} industries | {clusters ? `${numClusters} clusters` : ""} | iter {iteration}/{maxIter}
        </div>
        {hovered && (
          <div className="projector-tooltip" style={{
            left: Math.min(tooltipPos.current.x + 16, (canvasRef.current?.parentElement?.offsetWidth || 600) - 300),
            top: tooltipPos.current.y - 10,
          }}>
            <div className="projector-tooltip-title">{hovered.title}</div>
            <div className="projector-tooltip-meta">
              {hovered.industry}
              {clusters && clusters.assignments && (() => {
                const idx = points.findIndex(p => p.id === hovered.id);
                const cid = clusters.assignments[idx];
                const label = clusters.labels?.[String(cid)];
                return label ? ` | ${label}` : "";
              })()}
            </div>
          </div>
        )}
      </div>

      {/* Right panel — Search & Details */}
      <div className="projector-panel projector-panel-right">
        <div className="projector-panel-title">Search & Inspect</div>

        <div className="projector-section">
          <input type="text" className="projector-search" placeholder="Search case studies..."
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
        </div>

        {selected && (
          <div className="projector-section">
            <div className="projector-panel-title">Selected</div>
            <div className="projector-detail">
              <div className="projector-detail-title">{selected.title}</div>
              <div className="projector-detail-field">Industry</div>
              <div className="projector-detail-value">
                <span className="projector-filter-dot" style={{ background: industryColors[selected.industry], display: "inline-block", marginRight: 6, verticalAlign: "middle" }} />
                {selected.industry}
              </div>
              {clusters && clusters.assignments && (() => {
                const idx = points?.findIndex(p => p.id === selected.id);
                if (idx === undefined || idx < 0) return null;
                const cid = clusters.assignments[idx];
                const label = clusters.labels?.[String(cid)];
                if (!label) return null;
                return <>
                  <div className="projector-detail-field">Cluster</div>
                  <div className="projector-detail-value" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span className="projector-filter-dot" style={{ background: CLUSTER_COLORS[cid % CLUSTER_COLORS.length] }} />
                    {label}
                  </div>
                </>;
              })()}
              {selected.technologies && <>
                <div className="projector-detail-field">Technologies</div>
                <div className="projector-detail-value">{selected.technologies}</div>
              </>}
            </div>
          </div>
        )}

        {clusters && clusters.labels && (
          <div className="projector-section">
            <div className="projector-panel-title">Clusters</div>
            {Object.entries(clusters.labels).sort(([a],[b]) => +a - +b).map(([cid, label]) => {
              const count = clusters.assignments.filter(a => a === +cid).length;
              const color = CLUSTER_COLORS[+cid % CLUSTER_COLORS.length];
              return (
                <div key={cid} className="projector-detail" style={{ marginBottom: 6, padding: "8px 10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                    <span className="projector-filter-dot" style={{ background: color }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>{label}</span>
                  </div>
                  <div style={{ fontSize: 10, color: "rgba(255,255,255,0.35)" }}>{count} case studies</div>
                </div>
              );
            })}
          </div>
        )}

        <div className="projector-section">
          <div className="projector-panel-title">Legend</div>
          <div className="projector-legend">
            {Object.entries(industryColors).filter(([k]) => industries[k]).sort(([a],[b]) => a.localeCompare(b)).map(([ind, color]) => (
              <div className="projector-legend-item" key={ind}>
                <span className="projector-filter-dot" style={{ background: color }} />
                {ind}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Footer ----

function Footer() {
  return (
    <div className="cta-section">
      <h2>Explore phData's Experience</h2>
      <p>76 case studies across 22 industries and 40+ technologies.</p>
      <button className="cta-button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
        Back to Top <ArrowIcon />
      </button>
    </div>
  );
}

// ---- Cart View (inline page) ----

function CartView({ cart, removeFromCart, updateCartNote }) {
  const [checkingOut, setCheckingOut] = useState(false);
  const [checkoutDone, setCheckoutDone] = useState(false);

  const handleCheckout = async () => {
    if (cart.length === 0) return;
    setCheckingOut(true);
    try {
      const res = await fetch("/api/cart/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: cart.map(c => ({ id: c.id, title: c.title, url: c.url, industry: c.industry, technologies: c.technologies, challenge: c.challenge, solution: c.solution, results: c.results, cartNote: c.cartNote })) }),
      });
      const data = await res.json();
      if (data.success) {
        setCheckoutDone(true);
        // Open the summary page — it will auto-poll until the md file is ready
        window.open("/research-summary", "_blank");
      } else {
        alert("Checkout failed: " + (data.error || "Unknown error"));
      }
    } catch (err) {
      alert("Checkout error: " + err.message);
    } finally {
      setCheckingOut(false);
    }
  };

  const getTechs = (item) => (item.technologies || "").split(", ").filter(Boolean).slice(0, 3);

  return (
    <section className="section">
      <div className="section-header">
        <div>
          <div className="section-title">Research Cart</div>
          <div className="section-subtitle">{cart.length} case {cart.length === 1 ? "study" : "studies"} collected</div>
        </div>
        {cart.length > 0 && (
          <div>
            {checkoutDone ? (
              <div className="cart-checkout-done">
                <CheckIcon /> Research running —{" "}
                <a href="/research-summary" target="_blank" style={{ color: "var(--green-600)", textDecoration: "underline" }}>
                  View Summary
                </a>
              </div>
            ) : (
              <button className="cart-checkout-btn" onClick={handleCheckout} disabled={checkingOut} style={{ width: "auto", padding: "10px 24px" }}>
                {checkingOut ? "Launching..." : `Summarize ${cart.length} ${cart.length === 1 ? "Study" : "Studies"}`}
              </button>
            )}
          </div>
        )}
      </div>

      {cart.length === 0 ? (
        <div className="cart-empty-page">
          <div className="cart-empty-icon"><CartIcon size={48} /></div>
          <h3>No studies collected yet</h3>
          <p>Browse case studies or search, then click the <strong>+</strong> button to add them here.</p>
          <p>Add notes to guide how each study should appear in your research summary, then click <strong>Summarize</strong> to generate a markdown report.</p>
        </div>
      ) : (
        <div className="cart-grid">
          {cart.map((item, i) => (
            <div className="cart-card" key={item.id} style={{ animationDelay: `${i * 50}ms` }}>
              <div className="cart-card-top">
                <div className="cart-card-number">{i + 1}</div>
                <div className="cart-card-content">
                  <div className="cart-card-title">{item.title}</div>
                  <div className="cart-card-meta">
                    {item.industry && <span className="badge badge-industry">{item.industry}</span>}
                    {getTechs(item).map((t, j) => <span key={j} className="badge badge-tech">{t}</span>)}
                  </div>
                  {item.challenge && <div className="cart-card-excerpt">{item.challenge}</div>}
                </div>
                <button className="cart-remove-btn" onClick={() => removeFromCart(item.id)} title="Remove" aria-label="Remove from cart">
                  <TrashIcon />
                </button>
              </div>
              <div className="cart-card-note-wrap">
                <label className="cart-note-label">Summary guidance</label>
                <textarea
                  className="cart-note"
                  placeholder="e.g. 'focus on ROI metrics' or 'compare architecture to our fraud model'"
                  value={item.cartNote}
                  onChange={e => updateCartNote(item.id, e.target.value)}
                  rows={2}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ---- Mount ----

ReactDOM.createRoot(document.getElementById("root")).render(<App />);

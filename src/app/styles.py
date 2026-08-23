"""Scoped visual system for the artifact-only Streamlit dashboard."""

# ruff: noqa: E501 - CSS declarations stay grouped by selector for maintainability.

from __future__ import annotations

from typing import Any

DASHBOARD_CSS = """
:root {
  --navy-950: #06131f; --navy-900: #0a1d2d; --navy-800: #123047;
  --teal-400: #2dd4bf; --teal-200: #99f6e4; --amber-400: #fbbf24;
  --paper: #f5fbfb; --muted: #b9d3d1; --line: rgba(153, 246, 228, 0.18);
  --surface: rgba(18, 48, 71, 0.66); --radius-lg: 1.35rem; --radius-md: 0.95rem;
}
[data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 90% 0%, rgba(45,212,191,.11), transparent 30rem),
    linear-gradient(145deg, var(--navy-950), var(--navy-900)); color: var(--paper);
}
[data-testid="stMainBlockContainer"] { max-width: 78rem; padding-top: 2.75rem; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #071827, #081d2c); border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 1.1rem 0.85rem; }
.sidebar-brand { display: flex; align-items: center; gap: .7rem; margin: .35rem 0 1.15rem; }
.sidebar-mark {
  display: grid; place-items: center; width: 2.45rem; height: 2.45rem; border-radius: .8rem;
  background: var(--teal-400); color: var(--navy-950); font-weight: 900; letter-spacing: -.04em;
}
.sidebar-brand strong, .sidebar-brand small { display: block; }
.sidebar-brand strong { color: #fff; font-size: .98rem; }
.sidebar-brand small { color: var(--muted); font-size: .76rem; margin-top: .1rem; }
[data-testid="stSidebar"] [data-testid="stButton"] > button {
  min-height: 3rem; justify-content: flex-start; padding: .65rem .8rem; margin-top: .22rem;
  border-radius: .78rem; border: 1px solid transparent; color: #dcebea; font-weight: 700;
  text-align: left; transition: transform 150ms ease, background-color 150ms ease, border-color 150ms ease;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
  transform: translateX(2px); background: rgba(45,212,191,.1);
  border-color: rgba(45,212,191,.3); color: #fff;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(110deg, rgba(45,212,191,.2), rgba(45,212,191,.08));
  border-color: rgba(45,212,191,.56); color: #fff; box-shadow: inset 3px 0 0 var(--teal-400);
}
.nav-current { margin: .65rem 0 0; color: var(--teal-200); font-size: .75rem; }
.research-hero, .page-intro, .pattern-card, .content-section, .workflow-section,
.metric-guide, [data-testid="stMetric"], [data-testid="stTable"], .recommendation-card {
  animation: research-reveal 440ms cubic-bezier(.2,.75,.25,1) both;
}
.research-hero {
  display: block;
  padding: clamp(1.6rem,4vw,3.3rem); margin-bottom: 1.2rem; border: 1px solid var(--line);
  border-radius: var(--radius-lg); background: linear-gradient(135deg, rgba(23,66,91,.96), rgba(8,36,48,.9));
  box-shadow: 0 1.5rem 4rem rgba(0,0,0,.2);
}
.eyebrow {
  display: inline-block; color: var(--teal-200); font-size: .76rem; font-weight: 850;
  letter-spacing: .14em; text-transform: uppercase;
}
.research-hero h1, .page-intro h1 {
  max-width: 18ch; margin: .45rem 0 .8rem; color: #fff;
  font-size: clamp(2.15rem,5.2vw,4.4rem); line-height: 1.01; letter-spacing: -.045em;
}
.hero-subtitle, .page-intro p { max-width: 64ch; margin: 0; color: var(--muted); font-size: 1.08rem; line-height: 1.7; }
.pattern-grid, .metric-guide, .study-flow { display: grid; gap: .9rem; }
.pattern-grid { grid-template-columns: repeat(2,minmax(0,1fr)); margin: 1rem 0 .35rem; }
.pattern-card { position: relative; padding: 1.2rem 1.25rem; border: 1px solid rgba(45,212,191,.38); border-radius: var(--radius-md); background: var(--surface); }
.pattern-card.suspicious { border-color: rgba(251,191,36,.48); animation-delay: 80ms; }
.card-icon { float: right; display: grid; place-items: center; width: 1.8rem; height: 1.8rem; border-radius: 999px; background: rgba(45,212,191,.14); color: var(--teal-200); font-weight: 900; }
.suspicious .card-icon { background: rgba(251,191,36,.12); color: #fde68a; }
.pattern-card strong { display: block; color: #fff; font-size: 1rem; }
.pattern-card p, .study-step span { color: var(--muted); line-height: 1.55; }
.flow-line { margin-top: .75rem; color: var(--teal-200); font-family: ui-monospace, Consolas, monospace; letter-spacing: .08em; }
.suspicious .flow-line { color: #fde68a; }
.content-section { display: grid; grid-template-columns: auto minmax(0,1fr); gap: 1.1rem; margin: 3rem 0; padding: 1.5rem 0; border-block: 1px solid var(--line); }
.section-number { color: var(--teal-400); font-size: .78rem; font-weight: 850; }
.content-section h2, .workflow-section h2, .section-heading { margin: 0 0 .55rem; color: #fff; font-size: clamp(1.45rem,3vw,2rem); }
.content-section p { max-width: 70ch; margin: 0; color: var(--muted); line-height: 1.75; }
.workflow-section { margin: 2.4rem 0 1rem; }
.study-flow { grid-template-columns: repeat(4,minmax(0,1fr)); margin-top: 1rem; }
.study-step { padding: 1rem; border: 1px solid var(--line); border-radius: var(--radius-md); background: rgba(18,48,71,.46); }
.study-step b { display: grid; place-items: center; width: 1.7rem; height: 1.7rem; margin-bottom: .7rem; border-radius: 999px; background: var(--teal-400); color: var(--navy-950); }
.study-step strong { display: block; margin-bottom: .3rem; color: #fff; }
.reveal-delay-one { animation-delay: 100ms; } .reveal-delay-two { animation-delay: 170ms; }
.page-intro { padding: .8rem 0 1.5rem; } .page-intro h1 { font-size: clamp(2rem,4.5vw,3.7rem); }
.page-intro.compact { margin-bottom: 1rem; }
.metric-guide { grid-template-columns: repeat(3,minmax(0,1fr)); margin: 1rem 0 1.5rem; }
.metric-guide article { display: flex; gap: .75rem; padding: 1rem; border: 1px solid var(--line); border-radius: var(--radius-md); background: rgba(18,48,71,.46); }
.metric-guide article > span { color: var(--teal-200); font-size: 1.15rem; }
.metric-guide strong { color: #fff; }
.metric-guide p { margin: .25rem 0 0; color: var(--muted); font-size: .88rem; line-height: 1.5; }
[data-testid="stMetric"] { min-height: 7rem; padding: 1rem 1.1rem; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--surface); }
.section-heading { margin-top: 2.2rem; } .recommendation-heading { margin-bottom: .8rem; }
.table-meta { display: flex; justify-content: space-between; gap: 1rem; margin: .55rem 0 .45rem; color: var(--muted); font-size: .78rem; }
.table-meta > span { color: var(--teal-200); font-weight: 800; } .table-scroll-hint { display: none; }
[data-testid="stTable"] { overflow-x: auto; border: 1px solid var(--line); border-radius: var(--radius-md); background: rgba(8,29,44,.76); box-shadow: 0 .9rem 2.5rem rgba(0,0,0,.13); }
[data-testid="stTable"] table { width: 100%; min-width: 42rem; border-collapse: collapse; }
[data-testid="stTable"] thead tr { background: rgba(45,212,191,.12); }
[data-testid="stTable"] th { color: #fff !important; font-size: .78rem; letter-spacing: .035em; text-transform: uppercase; }
[data-testid="stTable"] th, [data-testid="stTable"] td { padding: .82rem .9rem !important; border-bottom: 1px solid rgba(153,246,228,.1) !important; }
[data-testid="stTable"] tbody tr:nth-child(even) { background: rgba(153,246,228,.035); }
[data-testid="stTable"] tbody tr:hover { background: rgba(45,212,191,.08); }
[data-testid="stTable"] th:not(:first-child), [data-testid="stTable"] td:not(:first-child) { text-align: right; }
[data-testid="stTable"] td:last-child { color: #fde68a !important; font-weight: 750; }
.recommendation-card { display: flex; gap: 1rem; align-items: flex-start; padding: 1.2rem; border: 1px solid rgba(251,191,36,.48); border-radius: var(--radius-md); background: linear-gradient(120deg, rgba(251,191,36,.11), rgba(18,48,71,.6)); }
.recommendation-star { color: var(--amber-400); font-size: 1.5rem; }
.recommendation-label { color: #fde68a; font-size: .75rem; font-weight: 850; letter-spacing: .08em; text-transform: uppercase; }
.recommendation-card h3 { margin: .25rem 0 .3rem; color: #fff; font-size: 1.4rem; }
.recommendation-card p { margin: 0; color: var(--muted); }
.recommendation-card small { display: block; margin-top: .55rem; color: var(--muted); }
button:focus-visible, a:focus-visible, [tabindex]:focus-visible { outline: 3px solid var(--amber-400) !important; outline-offset: 3px !important; border-radius: .35rem; }
@keyframes research-reveal { from { opacity: 0; transform: translateY(9px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 800px) {
  [data-testid="stMainBlockContainer"] { padding-inline: 1rem; padding-top: 1.6rem; }
  .pattern-grid, .study-flow, .metric-guide { grid-template-columns: 1fr; }
  [data-testid="stMetric"] { min-height: auto; } .table-scroll-hint { display: inline; }
  [data-testid="stTable"] { scrollbar-color: var(--teal-400) var(--navy-900); }
  [data-testid="stSidebar"] [data-testid="stButton"] > button { min-height: 2.75rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
}
"""


def apply_dashboard_styles(streamlit: Any) -> None:
    """Apply the scoped presentation CSS without altering saved evidence."""
    streamlit.markdown(f"<style>{DASHBOARD_CSS}</style>", unsafe_allow_html=True)

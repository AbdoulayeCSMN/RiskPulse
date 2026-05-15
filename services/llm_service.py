"""
LLM Service — Integration Grok (xAI).
======================================
Genere des insights en langage naturel a partir d'une analyse RiskPulse.

L'API Grok est compatible OpenAI : on utilise un client HTTP simple.
Cle API : stockee dans data/preferences.json (cle 'grok_api_key').
"""

import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Iterator

logger = logging.getLogger(__name__)


GROK_API_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_MODEL = "grok-2-latest"   # ou "grok-beta"
PREFS_PATH = Path("data") / "preferences.json"


def load_api_key() -> Optional[str]:
    """Recupere la cle API Grok depuis les preferences."""
    try:
        if PREFS_PATH.exists():
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("grok_api_key")
    except Exception:
        return None
    return None


def save_api_key(key: str):
    """Sauvegarde la cle API Grok."""
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if PREFS_PATH.exists():
        with open(PREFS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    data["grok_api_key"] = key.strip()
    with open(PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
#  CLIENT
# ─────────────────────────────────────────────

class GrokClient:
    """Client minimaliste pour l'API Grok (xAI). Compatible format OpenAI."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or load_api_key()
        self.model = model

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.4,
        max_tokens: int = 1024,
        timeout: int = 60,
    ) -> str:
        """
        Envoie un chat completion et retourne le texte.
        messages : [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        if not self.api_key:
            raise RuntimeError("Grok API key not configured. Add it in Settings.")

        body = json.dumps({
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }).encode("utf-8")

        req = urllib.request.Request(
            GROK_API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type":  "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Grok API error {e.code}: {err_body[:300]}")
        except Exception as e:
            raise RuntimeError(f"Grok request failed: {e}")

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected Grok response: {data}")


# ─────────────────────────────────────────────
#  PROMPTS PREDEFINIS
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are RiskPulse AI Analyst. You analyze graph-based risk \
intelligence reports. Your output is concise, structured, and actionable.

Rules:
- Always answer in the language of the user's question (auto-detect).
- Be specific: name the entities, cite the numerical scores.
- Avoid generic phrases like "this analysis shows".
- Structure with markdown: short bullets, no long paragraphs.
- If data is insufficient, say so plainly.
"""


def build_analysis_context(analysis: dict) -> str:
    """Construit un contexte textuel compact a partir d'une analyse RiskPulse."""
    if not analysis:
        return "No analysis available."

    stats = analysis.get("stats", {})
    entities = analysis.get("nlp", {}).get("entities", [])
    relations = analysis.get("nlp", {}).get("relations", [])
    centrality = analysis.get("centrality", {})
    comparison = analysis.get("comparison", {}).get("comparison", {})

    lines = []
    lines.append(f"# RiskPulse Analysis Context")
    lines.append(f"Entities: {stats.get('nb_entities', 0)}  | "
                 f"Relations: {stats.get('nb_relations', 0)}  | "
                 f"Density: {stats.get('density', 0):.3f}  | "
                 f"Components: {stats.get('nb_components', 0)}")
    lines.append("")

    # Top entities
    lines.append("## Top entities")
    for e in entities[:15]:
        lines.append(f"- {e.get('name','')} ({e.get('type_label','')}, freq={e.get('frequency','')})")
    lines.append("")

    # Relations
    lines.append("## Top relations")
    for r in relations[:15]:
        src = r.get('source', '').replace('_', ' ')
        tgt = r.get('target', '').replace('_', ' ')
        lines.append(f"- {src} -> {tgt} (weight={r.get('weight', 0):.1f})")
    lines.append("")

    # Critical nodes
    crit = centrality.get("critical_nodes", [])[:5]
    if crit:
        lines.append("## Top 5 critical nodes (composite score)")
        for n in crit:
            lines.append(f"- {n.get('name','')} : composite={n.get('composite',0):.3f} "
                         f"(pagerank={n.get('pagerank',0):.3f}, "
                         f"betweenness={n.get('betweenness',0):.3f}, "
                         f"degree={n.get('degree','')}, freq={n.get('frequency','')})")
        lines.append("")

    # Hidden critical
    hidden = centrality.get("hidden_critical", [])
    if hidden:
        lines.append("## Hidden critical nodes (low mention but high structural weight)")
        for n in hidden[:5]:
            lines.append(f"- {n.get('name','')} : {n.get('reason','')}")
        lines.append("")

    # Model comparison
    if comparison:
        lines.append("## Model comparison")
        lines.append(f"- IsolationForest: {comparison.get('n_anomalies_a', 0)} anomalies")
        lines.append(f"- GraphBased: {comparison.get('n_anomalies_b', 0)} anomalies")
        lines.append(f"- Agreement: {comparison.get('agreement_rate', 0):.0%}")
        lines.append(f"- Key insight: {comparison.get('key_insight', '')}")
        only_b = comparison.get("only_b_detects", [])
        if only_b:
            lines.append("- Entities flagged only by GraphBased (systemic risk):")
            for n in only_b[:5]:
                lines.append(f"  · {n.get('node_name','')} : {n.get('explanation','')}")

    return "\n".join(lines)


def generate_executive_summary(client: GrokClient, analysis: dict,
                                language: str = "en") -> str:
    """Genere un resume executif structure d'une analyse."""
    lang_name = {
        "fr": "French", "en": "English", "ar": "Arabic",
        "it": "Italian", "es": "Spanish",
    }.get(language, "English")

    context = build_analysis_context(analysis)
    user_prompt = f"""Analyze this RiskPulse intelligence report and produce \
a concise executive summary in {lang_name}.

Structure your response as:

### Key Findings
- 3 to 5 bullets, the most important takeaways

### Systemic Risks
- 2 to 4 specific risks detected, citing entities and scores

### Hidden Critical Nodes
- Explain which under-mentioned entities deserve attention and why

### Recommended Actions
- 3 concrete recommendations

Be specific. Cite entity names and numerical scores from the data.

---

{context}
"""
    return client.chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ], temperature=0.35, max_tokens=1500)


def ask_question(client: GrokClient, analysis: dict, question: str,
                  language: str = "en") -> str:
    """Repond a une question libre de l'utilisateur sur l'analyse."""
    lang_name = {
        "fr": "French", "en": "English", "ar": "Arabic",
        "it": "Italian", "es": "Spanish",
    }.get(language, "English")

    context = build_analysis_context(analysis)
    user_prompt = f"""You have access to this RiskPulse analysis.
Answer the user's question in {lang_name}. Be specific and cite data.

# DATA
{context}

# QUESTION
{question}
"""
    return client.chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ], temperature=0.4, max_tokens=900)

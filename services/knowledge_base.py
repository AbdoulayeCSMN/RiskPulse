"""
RiskPulse — Knowledge Base persistante (SQLite).

Chaque analyse y est enregistree. Les entites sont resolues entre analyses
via un matching flou (Levenshtein-like via difflib) pour identifier une
meme entite mentionnee sous plusieurs orthographes.

L'idee fondamentale : RiskPulse devient une *base d'intelligence qui
s'enrichit a chaque utilisation*. Plus on l'utilise, plus elle vaut.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data") / "knowledge.db"


# ─────────────────────────────────────────────
#  SCHEMA
# ─────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT    NOT NULL,
    title         TEXT,
    text_hash     TEXT,
    text_excerpt  TEXT,
    n_entities    INTEGER,
    n_relations   INTEGER,
    total_time    REAL,
    crisis_top    TEXT,
    crisis_sim    REAL,
    full_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_analyses_timestamp ON analyses(timestamp);

CREATE TABLE IF NOT EXISTS entities (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT    UNIQUE NOT NULL,
    type_label     TEXT,
    first_seen     TEXT,
    last_seen      TEXT,
    n_analyses     INTEGER DEFAULT 0,
    total_mentions INTEGER DEFAULT 0,
    avg_risk_score REAL,
    max_risk_score REAL,
    trend          TEXT
);
CREATE INDEX IF NOT EXISTS idx_entities_canonical ON entities(canonical_name);

CREATE TABLE IF NOT EXISTS entity_appearances (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id    INTEGER NOT NULL,
    analysis_id  INTEGER NOT NULL,
    timestamp    TEXT,
    raw_name     TEXT,
    risk_score   REAL,
    verdict      TEXT,
    drivers_json TEXT,
    frequency    INTEGER,
    FOREIGN KEY (entity_id)   REFERENCES entities(id),
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
);
CREATE INDEX IF NOT EXISTS idx_appear_entity ON entity_appearances(entity_id);

CREATE TABLE IF NOT EXISTS entity_cooccurrences (
    entity_a INTEGER NOT NULL,
    entity_b INTEGER NOT NULL,
    count    INTEGER DEFAULT 1,
    PRIMARY KEY (entity_a, entity_b)
);

-- ─── Etape 2 : Monitoring continu ───

CREATE TABLE IF NOT EXISTS watchlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id  INTEGER,
    name       TEXT NOT NULL,
    added_at   TEXT,
    threshold  REAL DEFAULT 0.6,
    enabled    INTEGER DEFAULT 1,
    notes      TEXT,
    last_score REAL,
    last_check TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);
CREATE INDEX IF NOT EXISTS idx_watchlist_enabled ON watchlist(enabled);

CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT UNIQUE NOT NULL,
    label       TEXT,
    type        TEXT NOT NULL,   -- 'rss' | 'url'
    enabled     INTEGER DEFAULT 1,
    added_at    TEXT,
    last_check  TEXT,
    last_status TEXT,
    items_seen  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sources_enabled ON sources(enabled);

CREATE TABLE IF NOT EXISTS source_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id  INTEGER NOT NULL,
    item_hash  TEXT NOT NULL,
    title      TEXT,
    url        TEXT,
    published  TEXT,
    fetched_at TEXT,
    analyzed   INTEGER DEFAULT 0,
    analysis_id INTEGER,
    FOREIGN KEY (source_id)   REFERENCES sources(id),
    FOREIGN KEY (analysis_id) REFERENCES analyses(id),
    UNIQUE(source_id, item_hash)
);
CREATE INDEX IF NOT EXISTS idx_items_source ON source_items(source_id);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    watchlist_id INTEGER,
    entity_name  TEXT,
    score        REAL,
    delta        REAL,
    verdict      TEXT,
    analysis_id  INTEGER,
    source_url   TEXT,
    title        TEXT,
    message      TEXT,
    seen         INTEGER DEFAULT 0,
    FOREIGN KEY (watchlist_id) REFERENCES watchlist(id),
    FOREIGN KEY (analysis_id)  REFERENCES analyses(id)
);
CREATE INDEX IF NOT EXISTS idx_alerts_seen ON alerts(seen);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);

-- ─── Etape 3 : Enrichissement externe (Wikidata / Wikipedia) ───

CREATE TABLE IF NOT EXISTS entity_enrichment (
    entity_id          INTEGER PRIMARY KEY,
    wikidata_id        TEXT,
    wikidata_label     TEXT,
    wikidata_desc      TEXT,
    wikipedia_title    TEXT,
    wikipedia_url      TEXT,
    wikipedia_summary  TEXT,
    type_label         TEXT,
    type_qid           TEXT,
    country            TEXT,
    country_qid        TEXT,
    city               TEXT,
    sector             TEXT,
    founded            TEXT,
    employees          INTEGER,
    revenue            TEXT,
    website            TEXT,
    parent_org         TEXT,
    subsidiaries_json  TEXT,
    raw_json           TEXT,
    enriched_at        TEXT,
    status             TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);
"""


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

# Suffixes corporates à retirer pour la normalisation
_CORP_SUFFIXES = (
    r"\b(sa|sarl|sas|s\.a\.|s\.a\.r\.l\.|s\.a\.s\.|"
    r"inc|inc\.|ltd|ltd\.|llc|gmbh|ag|spa|s\.p\.a\.|"
    r"corp|corp\.|corporation|company|cie|"
    r"holding|holdings|group|groupe|partners|"
    r"international|maroc|morocco)\b"
)

_ARTICLES = re.compile(
    r"^(le |la |les |l\'|un |une |des |the |a |an )",
    flags=re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    """
    Normalise un nom d'entite pour le matching cross-analyses.
    'Investcorp Maroc' / 'INVESTCORP MAROC SA' / 'Investcorp' -> mêmes -ish.
    """
    n = name.strip().lower()
    n = _ARTICLES.sub("", n)
    n = re.sub(_CORP_SUFFIXES, " ", n, flags=re.IGNORECASE)
    n = re.sub(r"[^a-z0-9À-ſ ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _similarity(a: str, b: str) -> float:
    """Ratio de similarite Levenshtein-like via difflib."""
    return SequenceMatcher(None, a, b).ratio()


# ─────────────────────────────────────────────
#  KNOWLEDGE BASE
# ─────────────────────────────────────────────

@dataclass
class EntitySummary:
    """Resume agregé d'une entite a travers toutes les analyses."""
    id:              int
    canonical_name:  str
    display_name:    str   # le nom le plus "joli" rencontre
    type_label:      str
    first_seen:      str
    last_seen:       str
    n_analyses:      int
    total_mentions:  int
    avg_risk_score:  float
    max_risk_score:  float
    trend:           str   # "rising" / "falling" / "stable"


class KnowledgeBase:
    """Couche persistante au-dessus de SQLite. Thread-safe par lock global."""

    # Seuil de similarite pour considerer 2 noms comme la meme entite
    MATCH_THRESHOLD = 0.85

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    @contextmanager
    def _conn(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _init_schema(self):
        with self._conn() as c:
            c.executescript(_SCHEMA)
        logger.info(f"KnowledgeBase initialisee : {self.db_path}")

    # ── Sauvegarde d'une analyse ───────────────

    def save_analysis(self, analysis: dict, text: str) -> int:
        """
        Persiste une analyse complete + extrait toutes ses entites pour le KG.
        Retourne l'id de l'analyse.
        """
        timestamp = analysis.get("timestamp") or datetime.now().isoformat()
        text_hash = str(abs(hash(text)))[:16]
        text_excerpt = text[:200].replace("\n", " ")
        stats = analysis.get("stats", {})

        ri = analysis.get("risk_intel", {})
        crisis_matches = ri.get("crisis_matches", [])
        crisis_top  = crisis_matches[0]["name"] if crisis_matches else None
        crisis_sim  = crisis_matches[0]["similarity"] if crisis_matches else None

        # Titre auto : prend le scenario si dispo, sinon les 2 premieres entites
        title = analysis.get("title")
        if not title:
            entities = analysis.get("nlp", {}).get("entities", [])
            if entities:
                title = " · ".join(e.get("name", "") for e in entities[:2])
            else:
                title = "Untitled"

        with self._conn() as c:
            cur = c.execute("""
                INSERT INTO analyses
                  (timestamp, title, text_hash, text_excerpt,
                   n_entities, n_relations, total_time,
                   crisis_top, crisis_sim, full_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, title, text_hash, text_excerpt,
                stats.get("nb_entities", 0),
                stats.get("nb_relations", 0),
                analysis.get("total_time", 0.0),
                crisis_top, crisis_sim,
                json.dumps(analysis, ensure_ascii=False, default=str),
            ))
            analysis_id = cur.lastrowid

        # Indexation des entites
        self._index_entities(analysis_id, analysis, timestamp)
        logger.info(f"Analysis #{analysis_id} sauvegardee dans la KB")
        return analysis_id

    def _index_entities(self, analysis_id: int, analysis: dict, timestamp: str):
        entities = analysis.get("nlp", {}).get("entities", [])
        risk_profiles = analysis.get("risk_intel", {}).get("profiles", [])

        # Lookup map node_id -> risk profile
        risk_by_id = {p["node_id"]: p for p in risk_profiles}

        entity_ids: list[int] = []
        for ent in entities:
            raw_name = ent.get("name", "")
            type_label = ent.get("type_label", "")
            freq = ent.get("frequency", 1)
            node_id = ent.get("id", "")

            profile = risk_by_id.get(node_id, {})
            score = profile.get("score", 0.0)
            verdict = profile.get("verdict", "")
            drivers = profile.get("drivers", [])

            eid = self._upsert_entity(
                raw_name=raw_name,
                type_label=type_label,
                timestamp=timestamp,
                score=score,
            )
            entity_ids.append(eid)
            self._insert_appearance(
                entity_id=eid,
                analysis_id=analysis_id,
                timestamp=timestamp,
                raw_name=raw_name,
                score=score,
                verdict=verdict,
                drivers=drivers,
                frequency=freq,
            )

        # Co-occurrences
        for i, a in enumerate(entity_ids):
            for b in entity_ids[i+1:]:
                if a == b:
                    continue
                lo, hi = (a, b) if a < b else (b, a)
                self._bump_cooccurrence(lo, hi)

    def _upsert_entity(self, raw_name: str, type_label: str,
                       timestamp: str, score: float) -> int:
        """Trouve ou cree une entite canonique. Met a jour les stats agregees."""
        canonical = _normalize_name(raw_name)
        if not canonical:
            canonical = raw_name.lower()

        with self._conn() as c:
            # Match exact d'abord
            row = c.execute(
                "SELECT id, n_analyses, total_mentions, avg_risk_score, "
                "max_risk_score FROM entities WHERE canonical_name=?",
                (canonical,)
            ).fetchone()

            # Sinon match flou
            if not row:
                candidates = c.execute(
                    "SELECT id, canonical_name, n_analyses, total_mentions, "
                    "avg_risk_score, max_risk_score FROM entities"
                ).fetchall()
                best = None
                best_sim = 0.0
                for cand in candidates:
                    sim = _similarity(canonical, cand["canonical_name"])
                    if sim > best_sim and sim >= self.MATCH_THRESHOLD:
                        best = cand
                        best_sim = sim
                row = best

            if row:
                # Update : moyenne ponderee
                eid = row["id"]
                new_n = row["n_analyses"] + 1
                new_mentions = (row["total_mentions"] or 0) + 1
                # Moyenne mobile simple
                old_avg = row["avg_risk_score"] or 0.0
                new_avg = (old_avg * row["n_analyses"] + score) / max(1, new_n)
                new_max = max(row["max_risk_score"] or 0.0, score)
                # Tendance basée sur l'écart vs moyenne
                if score > old_avg + 0.05:
                    trend = "rising"
                elif score < old_avg - 0.05:
                    trend = "falling"
                else:
                    trend = "stable"
                c.execute("""
                    UPDATE entities SET
                      last_seen=?, n_analyses=?, total_mentions=?,
                      avg_risk_score=?, max_risk_score=?, trend=?
                    WHERE id=?
                """, (timestamp, new_n, new_mentions, new_avg, new_max, trend, eid))
                return eid

            # Creation
            cur = c.execute("""
                INSERT INTO entities
                  (canonical_name, type_label, first_seen, last_seen,
                   n_analyses, total_mentions, avg_risk_score, max_risk_score, trend)
                VALUES (?, ?, ?, ?, 1, 1, ?, ?, 'new')
            """, (canonical, type_label, timestamp, timestamp, score, score))
            return cur.lastrowid

    def _insert_appearance(self, **kwargs):
        with self._conn() as c:
            c.execute("""
                INSERT INTO entity_appearances
                  (entity_id, analysis_id, timestamp, raw_name,
                   risk_score, verdict, drivers_json, frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                kwargs["entity_id"], kwargs["analysis_id"],
                kwargs["timestamp"], kwargs["raw_name"],
                kwargs["score"], kwargs["verdict"],
                json.dumps(kwargs["drivers"], ensure_ascii=False),
                kwargs["frequency"],
            ))

    def _bump_cooccurrence(self, a: int, b: int):
        with self._conn() as c:
            c.execute("""
                INSERT INTO entity_cooccurrences (entity_a, entity_b, count)
                VALUES (?, ?, 1)
                ON CONFLICT(entity_a, entity_b) DO UPDATE SET count=count+1
            """, (a, b))

    # ── Lectures ───────────────────────────────

    def list_entities(self, search: str = "", limit: int = 200) -> list[EntitySummary]:
        """Liste toutes les entites connues, optionnellement filtrees par recherche."""
        with self._conn() as c:
            q = ("SELECT e.*, ("
                 "SELECT raw_name FROM entity_appearances "
                 "WHERE entity_id=e.id ORDER BY id DESC LIMIT 1) AS display_name "
                 "FROM entities e ")
            args: list = []
            if search.strip():
                q += "WHERE e.canonical_name LIKE ? "
                args.append(f"%{search.lower()}%")
            q += "ORDER BY e.avg_risk_score DESC, e.n_analyses DESC LIMIT ?"
            args.append(limit)
            rows = c.execute(q, args).fetchall()

        return [
            EntitySummary(
                id=r["id"],
                canonical_name=r["canonical_name"],
                display_name=r["display_name"] or r["canonical_name"].title(),
                type_label=r["type_label"] or "",
                first_seen=r["first_seen"] or "",
                last_seen=r["last_seen"] or "",
                n_analyses=r["n_analyses"] or 0,
                total_mentions=r["total_mentions"] or 0,
                avg_risk_score=r["avg_risk_score"] or 0.0,
                max_risk_score=r["max_risk_score"] or 0.0,
                trend=r["trend"] or "stable",
            )
            for r in rows
        ]

    def get_entity_history(self, entity_id: int) -> dict:
        """Detail complet : toutes les analyses + co-occurrences + timeline."""
        with self._conn() as c:
            entity = c.execute("SELECT * FROM entities WHERE id=?",
                                (entity_id,)).fetchone()
            if not entity:
                return {}

            appearances = c.execute("""
                SELECT a.id AS aid, a.timestamp, a.title, a.text_excerpt,
                       a.crisis_top, a.crisis_sim,
                       ea.raw_name, ea.risk_score, ea.verdict, ea.drivers_json,
                       ea.frequency
                FROM entity_appearances ea
                JOIN analyses a ON ea.analysis_id = a.id
                WHERE ea.entity_id=?
                ORDER BY a.timestamp ASC
            """, (entity_id,)).fetchall()

            # Co-occurrences
            neighbors = c.execute("""
                SELECT
                  CASE WHEN entity_a=? THEN entity_b ELSE entity_a END AS nb_id,
                  count
                FROM entity_cooccurrences
                WHERE entity_a=? OR entity_b=?
                ORDER BY count DESC LIMIT 12
            """, (entity_id, entity_id, entity_id)).fetchall()

            neighbor_details = []
            for n in neighbors:
                nb = c.execute("SELECT canonical_name, avg_risk_score FROM entities "
                               "WHERE id=?", (n["nb_id"],)).fetchone()
                if nb:
                    neighbor_details.append({
                        "name":     nb["canonical_name"].title(),
                        "score":    nb["avg_risk_score"] or 0.0,
                        "count":    n["count"],
                    })

        return {
            "entity":      dict(entity),
            "appearances": [dict(a) for a in appearances],
            "neighbors":   neighbor_details,
        }

    def stats(self) -> dict:
        """Stats globales pour le header de la vue Knowledge Base."""
        with self._conn() as c:
            n_analyses = c.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
            n_entities = c.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            n_appearances = c.execute("SELECT COUNT(*) FROM entity_appearances").fetchone()[0]
            avg_risk = c.execute(
                "SELECT AVG(avg_risk_score) FROM entities WHERE avg_risk_score>0"
            ).fetchone()[0] or 0.0

        return {
            "n_analyses":    n_analyses,
            "n_entities":    n_entities,
            "n_appearances": n_appearances,
            "avg_risk":      avg_risk,
        }

    def list_recent_analyses(self, limit: int = 20) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("""
                SELECT id, timestamp, title, n_entities, n_relations,
                       crisis_top, crisis_sim
                FROM analyses
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def clear_all(self):
        """Reset complet — pour tests/debug."""
        with self._conn() as c:
            c.execute("DELETE FROM entity_enrichment")
            c.execute("DELETE FROM entity_cooccurrences")
            c.execute("DELETE FROM entity_appearances")
            c.execute("DELETE FROM entities")
            c.execute("DELETE FROM analyses")

    # ── Enrichissement externe ────────────────

    def get_enrichment(self, entity_id: int) -> Optional[dict]:
        """Recupere l'enrichissement deja en cache, sinon None."""
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM entity_enrichment WHERE entity_id=?",
                (entity_id,)
            ).fetchone()
            if row:
                return dict(row)
        return None

    def save_enrichment(self, entity_id: int, data: dict):
        """Persiste un enrichissement (upsert)."""
        with self._conn() as c:
            c.execute("DELETE FROM entity_enrichment WHERE entity_id=?", (entity_id,))
            c.execute("""
                INSERT INTO entity_enrichment
                  (entity_id, wikidata_id, wikidata_label, wikidata_desc,
                   wikipedia_title, wikipedia_url, wikipedia_summary,
                   type_label, type_qid, country, country_qid, city,
                   sector, founded, employees, revenue, website,
                   parent_org, subsidiaries_json, raw_json,
                   enriched_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?)
            """, (
                entity_id,
                data.get("wikidata_id"),
                data.get("wikidata_label"),
                data.get("wikidata_desc"),
                data.get("wikipedia_title"),
                data.get("wikipedia_url"),
                data.get("wikipedia_summary"),
                data.get("type_label"),
                data.get("type_qid"),
                data.get("country"),
                data.get("country_qid"),
                data.get("city"),
                data.get("sector"),
                data.get("founded"),
                data.get("employees"),
                data.get("revenue"),
                data.get("website"),
                data.get("parent_org"),
                data.get("subsidiaries"),
                data.get("raw"),
                datetime.now().isoformat(),
                data.get("status", "enriched"),
            ))

    def enrich_entity(self, entity_id: int, lang: str = "fr",
                       force: bool = False) -> Optional[dict]:
        """
        Enrichit une entite via Wikidata + Wikipedia.
        Si deja enrichie et !force, retourne le cache.
        Bloquant — a appeler depuis un thread.
        """
        if not force:
            cached = self.get_enrichment(entity_id)
            if cached and cached.get("status") == "enriched":
                return cached

        # Recupere le nom canonique
        with self._conn() as c:
            row = c.execute(
                "SELECT canonical_name FROM entities WHERE id=?",
                (entity_id,)
            ).fetchone()
            if not row:
                return None
            name = row["canonical_name"]

        # Affiche-friendly : retire les suffixes/articles deja normalises
        from .enrichment import enrich_name
        data = enrich_name(name.title(), lang=lang)

        self.save_enrichment(entity_id, data.as_dict())
        return self.get_enrichment(entity_id)


# Singleton ergonomique
_kb_instance: Optional[KnowledgeBase] = None

def get_kb() -> KnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance

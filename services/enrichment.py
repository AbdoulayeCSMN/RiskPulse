"""
Enrichissement externe — Wikidata + Wikipedia (sans cle API).

Pour chaque entite locale, on cherche la correspondance Wikidata via
l'API officielle, puis on enrichit avec :
  - QID Wikidata
  - Label / description multilingue
  - Type officiel (P31, instance of)
  - Pays (P17), siege (P159), ville (P276)
  - Date de fondation (P571)
  - Industrie / secteur (P452)
  - Employes (P1128)
  - Revenu (P2139)
  - Site web officiel (P856)
  - Maison mere (P749), filiales (P355)
  - Resume Wikipedia + URL

Aucune cle API. Gratuit, sans limite stricte sauf rate-limiting raisonnable.
"""

from __future__ import annotations
import json
import logging
import re
import urllib.request
import urllib.parse
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


WD_SEARCH_URL  = "https://www.wikidata.org/w/api.php"
WD_ENTITY_URL  = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
WP_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"


HEADERS = {
    "User-Agent": "RiskPulse/1.0 (https://riskpulse.local; contact@riskpulse.local)",
    "Accept": "application/json",
}


# Type labels FR/EN pour les instances Wikidata les plus communes
TYPE_LABELS = {
    "Q4830453": ("Organisation", "Business"),
    "Q43229":   ("Organisation", "Organization"),
    "Q891723":  ("Société",      "Public company"),
    "Q4830453": ("Société",      "Business"),
    "Q1456832": ("Entreprise",   "Multinational corp."),
    "Q22687":   ("Banque",       "Bank"),
    "Q1058914": ("Société",      "Software company"),
    "Q5":       ("Personne",     "Person"),
    "Q6256":    ("Pays",         "Country"),
    "Q515":     ("Ville",        "City"),
    "Q1320047": ("Holding",      "Holding company"),
    "Q161726":  ("Multinationale", "Multinational"),
    "Q740752":  ("Banque centrale", "Central bank"),
    "Q484652":  ("Société internationale", "International org."),
}


@dataclass
class EnrichmentData:
    wikidata_id:       Optional[str] = None
    wikidata_label:    Optional[str] = None
    wikidata_desc:     Optional[str] = None
    wikipedia_title:   Optional[str] = None
    wikipedia_url:     Optional[str] = None
    wikipedia_summary: Optional[str] = None
    type_label:        Optional[str] = None
    type_qid:          Optional[str] = None
    country:           Optional[str] = None
    country_qid:       Optional[str] = None
    city:              Optional[str] = None
    sector:            Optional[str] = None
    founded:           Optional[str] = None
    employees:         Optional[int] = None
    revenue:           Optional[str] = None
    website:           Optional[str] = None
    parent_org:        Optional[str] = None
    subsidiaries:      Optional[list] = None
    raw:               Optional[dict] = None
    status:            str = "not_found"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["subsidiaries"] = json.dumps(self.subsidiaries) if self.subsidiaries else None
        d["raw"] = json.dumps(self.raw, ensure_ascii=False) if self.raw else None
        return d


# ─────────────────────────────────────────────
#  HTTP helpers
# ─────────────────────────────────────────────

def _http_get_json(url: str, params: dict = None, timeout: int = 12) -> Optional[dict]:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"HTTP fail {url}: {e}")
        return None


# ─────────────────────────────────────────────
#  Wikidata search + entity fetch
# ─────────────────────────────────────────────

def _search_wikidata(name: str, lang: str = "fr") -> Optional[str]:
    """Cherche le QID Wikidata correspondant a un nom."""
    data = _http_get_json(WD_SEARCH_URL, {
        "action":   "wbsearchentities",
        "format":   "json",
        "search":   name,
        "language": lang,
        "limit":    3,
        "type":     "item",
    })
    if not data:
        return None
    results = data.get("search", [])
    if not results:
        # Retry with English
        if lang != "en":
            return _search_wikidata(name, "en")
        return None
    return results[0].get("id")


def _fetch_wikidata_entity(qid: str) -> Optional[dict]:
    """Recupere les claims complets d'une entite Wikidata par QID."""
    url = WD_ENTITY_URL.format(qid=qid)
    data = _http_get_json(url)
    if not data:
        return None
    return data.get("entities", {}).get(qid)


def _extract_claim(entity: dict, prop: str) -> Optional[str]:
    """Extrait la valeur d'une propriete Wikidata (claim)."""
    claims = entity.get("claims", {}).get(prop, [])
    if not claims:
        return None
    snak = claims[0].get("mainsnak", {})
    if snak.get("snaktype") != "value":
        return None
    val = snak.get("datavalue", {}).get("value")
    if isinstance(val, dict):
        if "id" in val:
            return val["id"]   # QID
        if "time" in val:
            return val["time"][1:11]   # YYYY-MM-DD
        if "amount" in val:
            try:
                return str(int(float(val["amount"])))
            except ValueError:
                return str(val["amount"])
        if "text" in val:
            return val["text"]
    return str(val) if val else None


def _extract_claims_list(entity: dict, prop: str, limit: int = 5) -> list[str]:
    claims = entity.get("claims", {}).get(prop, [])
    out = []
    for c in claims[:limit]:
        snak = c.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        val = snak.get("datavalue", {}).get("value")
        if isinstance(val, dict):
            if "id" in val:
                out.append(val["id"])
            elif "text" in val:
                out.append(val["text"])
    return out


def _label_of(qid: str, lang: str = "fr") -> Optional[str]:
    """Resout un QID en label lisible."""
    if not qid:
        return None
    if qid in TYPE_LABELS:
        return TYPE_LABELS[qid][0 if lang == "fr" else 1]
    data = _http_get_json(WD_SEARCH_URL, {
        "action":   "wbgetentities",
        "format":   "json",
        "ids":      qid,
        "props":    "labels",
        "languages": f"{lang}|en",
    })
    if not data:
        return None
    labels = data.get("entities", {}).get(qid, {}).get("labels", {})
    return (labels.get(lang) or labels.get("en") or {}).get("value")


# ─────────────────────────────────────────────
#  Wikipedia summary
# ─────────────────────────────────────────────

def _fetch_wikipedia_summary(title: str, lang: str = "fr") -> Optional[dict]:
    if not title:
        return None
    title_url = urllib.parse.quote(title.replace(" ", "_"))
    url = WP_SUMMARY_URL.format(lang=lang, title=title_url)
    data = _http_get_json(url, timeout=10)
    if not data or data.get("type") == "disambiguation":
        # Retry EN
        if lang != "en":
            return _fetch_wikipedia_summary(title, "en")
        return None
    return data


# ─────────────────────────────────────────────
#  Main enrichment function
# ─────────────────────────────────────────────

def enrich_name(name: str, lang: str = "fr") -> EnrichmentData:
    """
    Pipeline complet : nom -> EnrichmentData.
    Si rien trouve, status='not_found' et le reste est vide.
    """
    result = EnrichmentData()

    qid = _search_wikidata(name, lang=lang)
    if not qid:
        logger.info(f"No Wikidata match for: {name}")
        return result

    entity = _fetch_wikidata_entity(qid)
    if not entity:
        result.wikidata_id = qid
        result.status = "error"
        return result

    result.wikidata_id = qid
    result.raw = entity

    # Labels
    labels = entity.get("labels", {})
    descs = entity.get("descriptions", {})
    result.wikidata_label = (labels.get(lang) or labels.get("en") or {}).get("value")
    result.wikidata_desc = (descs.get(lang) or descs.get("en") or {}).get("value")

    # Type (P31)
    type_qid = _extract_claim(entity, "P31")
    if type_qid:
        result.type_qid = type_qid
        result.type_label = _label_of(type_qid, lang)

    # Pays (P17)
    country_qid = _extract_claim(entity, "P17")
    if country_qid:
        result.country_qid = country_qid
        result.country = _label_of(country_qid, lang)

    # Siege (P159) -> ville
    hq_qid = _extract_claim(entity, "P159")
    if hq_qid:
        result.city = _label_of(hq_qid, lang)

    # Secteur / industrie (P452)
    sector_qid = _extract_claim(entity, "P452")
    if sector_qid:
        result.sector = _label_of(sector_qid, lang)

    # Date de fondation (P571) ou date de naissance (P569)
    result.founded = _extract_claim(entity, "P571") or _extract_claim(entity, "P569")

    # Employes (P1128)
    emp = _extract_claim(entity, "P1128")
    if emp:
        try:
            result.employees = int(float(emp))
        except (ValueError, TypeError):
            pass

    # Revenu (P2139)
    rev = _extract_claim(entity, "P2139")
    if rev:
        result.revenue = rev

    # Site officiel (P856)
    result.website = _extract_claim(entity, "P856")

    # Maison mere (P749)
    parent_qid = _extract_claim(entity, "P749")
    if parent_qid:
        result.parent_org = _label_of(parent_qid, lang)

    # Filiales (P355)
    sub_qids = _extract_claims_list(entity, "P355", limit=5)
    if sub_qids:
        result.subsidiaries = [_label_of(q, lang) for q in sub_qids if _label_of(q, lang)]

    # Wikipedia
    wp_title = (entity.get("sitelinks", {})
                .get(f"{lang}wiki", {}).get("title"))
    if not wp_title:
        wp_title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    if wp_title:
        result.wikipedia_title = wp_title
        wp_data = _fetch_wikipedia_summary(wp_title, lang=lang)
        if wp_data:
            result.wikipedia_summary = wp_data.get("extract", "")[:600]
            result.wikipedia_url = wp_data.get("content_urls", {}).get("desktop", {}).get("page")

    result.status = "enriched"
    return result

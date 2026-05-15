"""
Feed Ingester — recupere des articles depuis RSS / URLs.

Pour la robustesse sans dependance externe lourde, on parse le RSS avec
xml.etree.ElementTree (stdlib). Si feedparser est dispo, on l'utilise.
"""

from __future__ import annotations
import logging
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (RiskPulse Monitoring) AppleWebKit/537.36",
    "Accept": "*/*",
}

# Sources prerecommandees (configurable, agnostique)
SUGGESTED_FEEDS = [
    {"url": "https://www.reuters.com/markets/finance/rss",
     "label": "Reuters Finance", "type": "rss"},
    {"url": "https://www.lemonde.fr/economie/rss_full.xml",
     "label": "Le Monde Economie", "type": "rss"},
    {"url": "https://feeds.feedburner.com/euronews/en/business",
     "label": "Euronews Business", "type": "rss"},
    {"url": "https://www.lesechos.fr/finance-marches/rss.xml",
     "label": "Les Echos Finance", "type": "rss"},
]


@dataclass
class FeedItem:
    title:     str
    summary:   str
    link:      str
    published: str = ""

    def as_text(self) -> str:
        """Concatene title + summary pour analyse NLP."""
        return f"{self.title}.\n\n{self.summary}"


# ─────────────────────────────────────────────
#  RSS PARSING
# ─────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Supprime balises HTML basiques."""
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<style.*?</style>",   " ", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_rss(url: str, timeout: int = 15, max_items: int = 10) -> list[FeedItem]:
    """
    Recupere et parse un flux RSS / Atom.
    Utilise feedparser si dispo (meilleure compat), sinon stdlib XML.
    """
    # ── Tentative 1 : feedparser ──
    try:
        import feedparser   # type: ignore
        d = feedparser.parse(url, request_headers=DEFAULT_HEADERS)
        items = []
        for e in d.entries[:max_items]:
            items.append(FeedItem(
                title=e.get("title", ""),
                summary=_strip_html(e.get("summary", "") or e.get("description", "")),
                link=e.get("link", ""),
                published=e.get("published", "") or e.get("updated", ""),
            ))
        return items
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"feedparser failed for {url}: {e}")

    # ── Tentative 2 : stdlib XML ──
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        items = _parse_rss_xml(root, max_items)
        return items
    except Exception as e:
        logger.exception(f"RSS fetch failed for {url}")
        raise RuntimeError(f"Cannot fetch {url}: {e}")


def _parse_rss_xml(root: ET.Element, max_items: int) -> list[FeedItem]:
    """Parse RSS 2.0 ou Atom 1.0 (stdlib)."""
    items: list[FeedItem] = []

    # RSS 2.0
    for it in root.iter():
        if it.tag.endswith("}item") or it.tag == "item":
            title = _findtext(it, "title")
            link = _findtext(it, "link")
            desc = _findtext(it, "description") or _findtext(it, "summary")
            pub = _findtext(it, "pubDate") or _findtext(it, "date")
            items.append(FeedItem(
                title=title or "",
                summary=_strip_html(desc or ""),
                link=link or "",
                published=pub or "",
            ))
        elif it.tag.endswith("}entry") or it.tag == "entry":
            # Atom
            title = _findtext(it, "title")
            link = ""
            for l in it.iter():
                if l.tag.endswith("}link") or l.tag == "link":
                    link = l.get("href") or l.text or ""
                    if link:
                        break
            content = _findtext(it, "content") or _findtext(it, "summary")
            pub = _findtext(it, "updated") or _findtext(it, "published")
            items.append(FeedItem(
                title=title or "",
                summary=_strip_html(content or ""),
                link=link,
                published=pub or "",
            ))
        if len(items) >= max_items:
            break
    return items


def _findtext(elem: ET.Element, local: str) -> str:
    """Cherche un sous-element par nom local (ignore namespace)."""
    for child in elem:
        if child.tag == local or child.tag.endswith(f"}}{local}"):
            return (child.text or "").strip()
    return ""


# ─────────────────────────────────────────────
#  URL SCRAPING (article direct)
# ─────────────────────────────────────────────

def fetch_url(url: str, timeout: int = 15) -> str:
    """Telecharge une URL et extrait le texte principal."""
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()
        article = soup.find("article") or soup.find("main") or soup.body
        text = article.get_text(separator="\n", strip=True) if article else ""
    except ImportError:
        text = _strip_html(html)

    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 40]
    return "\n\n".join(lines)

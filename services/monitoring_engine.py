"""
Monitoring Engine — l'agent qui travaille pour vous.

Orchestre :
  1. Boucle sur les sources actives (RSS / URLs)
  2. Pour chaque nouvel item (dedup par hash) : run analyse_text
  3. Pour chaque entite de la watchlist : check score vs threshold
  4. Si depasse seuil ou augmentation significative -> alerte enregistree

Conçu pour etre execute periodiquement (QTimer) ou a la demande.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional, Callable

from difflib import SequenceMatcher

from .knowledge_base import get_kb, _normalize_name
from .watchlist import get_watchlist, hash_item
from .feed_ingester import fetch_rss, fetch_url, FeedItem

logger = logging.getLogger(__name__)


# Seuils par defaut
DEFAULT_THRESHOLD = 0.6
DELTA_TRIGGER = 0.15   # une hausse de >0.15 declenche aussi une alerte
MIN_TEXT_LEN  = 80     # ignore les snippets RSS trop courts


# ─────────────────────────────────────────────
#  ENGINE
# ─────────────────────────────────────────────

class MonitoringEngine:
    """
    Le controller est injecte pour pouvoir appeler analyze_text().
    Singleton non-thread (instancie 1× depuis MainWindow).
    """

    def __init__(self, controller, on_alert: Optional[Callable] = None):
        self.controller = controller
        self.kb = get_kb()
        self.wl = get_watchlist()
        # callback : on_alert(alert_dict) -> notification UI
        self.on_alert = on_alert
        self._running = False

    # ── Cycle complet ─────────────────────────

    def run_cycle(self, max_items_per_source: int = 5) -> dict:
        """
        Lance un cycle de monitoring complet :
          - parcourt toutes les sources actives
          - analyse les nouveaux items
          - leve les alertes pour chaque entite de la watchlist
        Retourne un resume (n_sources, n_items, n_alerts).
        """
        if self._running:
            logger.info("Cycle deja en cours, skip")
            return {"skipped": True}

        self._running = True
        n_sources = 0
        n_items = 0
        n_alerts = 0
        errors: list[str] = []

        try:
            sources = self.wl.list_sources(enabled_only=True)
            watches = self.wl.list_watches(enabled_only=True)
            if not sources:
                return {"n_sources": 0, "n_items": 0, "n_alerts": 0,
                        "message": "No active sources"}
            if not watches:
                return {"n_sources": len(sources), "n_items": 0, "n_alerts": 0,
                        "message": "No watched entities"}

            for src in sources:
                n_sources += 1
                try:
                    nb_items, nb_alerts = self._process_source(
                        src, watches, max_items_per_source
                    )
                    n_items  += nb_items
                    n_alerts += nb_alerts
                except Exception as e:
                    logger.exception(f"Source {src['url']} failed")
                    self.wl.update_source_status(src["id"], f"ERROR: {e}")
                    errors.append(f"{src['label']}: {e}")
        finally:
            self._running = False

        return {
            "n_sources": n_sources, "n_items": n_items,
            "n_alerts":  n_alerts,  "errors":  errors,
            "timestamp": datetime.now().isoformat(),
        }

    def _process_source(self, src: dict, watches: list[dict],
                        max_items: int) -> tuple[int, int]:
        """Traite une source. Retourne (items_analyses, alertes_levees)."""
        url = src["url"]
        src_type = src["type"]

        if src_type == "rss":
            items = fetch_rss(url, max_items=max_items)
        else:
            # URL directe : un seul item (sauf si deja vu)
            text = fetch_url(url)
            items = [FeedItem(title=src["label"] or url, summary=text, link=url)]

        items_analyzed = 0
        alerts_raised = 0

        for it in items:
            text = it.as_text()
            if len(text) < MIN_TEXT_LEN:
                continue

            item_h = hash_item(it.link, it.title)
            if self.wl.is_item_seen(src["id"], item_h):
                continue   # deja traite

            # Run analyse complete
            try:
                analysis = self.controller.analyze_text(text)
            except Exception as e:
                logger.warning(f"analyze failed for {it.title}: {e}")
                continue

            if "error" in analysis:
                continue

            analysis_id = analysis.get("kb_id")
            self.wl.record_item(
                source_id=src["id"], item_hash=item_h,
                title=it.title, url=it.link, published=it.published,
                analysis_id=analysis_id,
            )
            items_analyzed += 1

            # Check alerts sur les watchlist entries
            alerts_raised += self._check_alerts(
                analysis, watches, it, analysis_id
            )

        self.wl.update_source_status(src["id"], "OK", items_added=items_analyzed)
        return items_analyzed, alerts_raised

    def _check_alerts(self, analysis: dict, watches: list[dict],
                       item: FeedItem, analysis_id: Optional[int]) -> int:
        """Pour chaque entite de la watchlist, regarde si elle est dans l'analyse."""
        ri = analysis.get("risk_intel", {})
        profiles = ri.get("profiles", [])
        if not profiles:
            return 0

        n = 0
        for watch in watches:
            target_name = watch["name"]
            target_norm = _normalize_name(target_name)

            # Cherche l'entite dans les profils (matching flou)
            best = None
            best_sim = 0.0
            for p in profiles:
                pname_norm = _normalize_name(p.get("name", ""))
                sim = SequenceMatcher(None, target_norm, pname_norm).ratio()
                if sim > best_sim and sim > 0.7:
                    best = p
                    best_sim = sim

            if not best:
                continue

            score = best.get("score", 0.0)
            verdict = best.get("verdict", "")
            threshold = watch.get("threshold") or DEFAULT_THRESHOLD
            previous = watch.get("last_score")
            delta = (score - previous) if previous is not None else 0.0

            # Conditions de declenchement :
            #  - score depasse le seuil ET (pas de previous OU previous < seuil)
            #  - OU augmentation > DELTA_TRIGGER
            should_alert = False
            reason = ""
            if score >= threshold and (previous is None or previous < threshold):
                should_alert = True
                reason = f"Risque depasse le seuil ({score:.2f} >= {threshold:.2f})"
            elif delta >= DELTA_TRIGGER:
                should_alert = True
                reason = f"Hausse significative (+{delta:.2f})"

            # Met a jour le dernier score quoi qu'il arrive
            self.wl.update_last_score(watch["id"], score)

            if should_alert:
                msg = (
                    f"{best.get('name','')} ({verdict}, score={score:.2f}). "
                    f"{reason}. Source : {item.title[:80]}"
                )
                alert_id = self.wl.record_alert(
                    watchlist_id=watch["id"],
                    entity_name=best.get("name", target_name),
                    score=score,
                    delta=delta,
                    verdict=verdict,
                    analysis_id=analysis_id,
                    source_url=item.link,
                    title=item.title,
                    message=msg,
                )
                n += 1
                if self.on_alert:
                    try:
                        self.on_alert({
                            "id":          alert_id,
                            "entity_name": best.get("name", target_name),
                            "score":       score,
                            "delta":       delta,
                            "verdict":     verdict,
                            "title":       item.title,
                            "source_url":  item.link,
                            "message":     msg,
                        })
                    except Exception:
                        logger.exception("on_alert callback failed")
        return n


# Singleton
_engine_instance: Optional[MonitoringEngine] = None

def get_engine(controller=None, on_alert=None) -> MonitoringEngine:
    global _engine_instance
    if _engine_instance is None:
        if controller is None:
            raise RuntimeError("MonitoringEngine needs controller on first init")
        _engine_instance = MonitoringEngine(controller, on_alert=on_alert)
    elif on_alert is not None:
        _engine_instance.on_alert = on_alert
    return _engine_instance

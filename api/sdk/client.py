"""
RiskPulse Python SDK
=====================
Client minimal pour interagir avec l'API REST RiskPulse.

Usage :
    from api.sdk import RiskPulseClient
    client = RiskPulseClient(api_key="rpk_...", base_url="http://localhost:8765")
    result = client.analyze("Bank Al-Maghrib a annonce ...")
    entities = client.list_entities(search="bank")
    forecast = client.forecast(entity_id=42, horizon_days=30)
"""

from __future__ import annotations
import json
import urllib.parse
import urllib.request
from typing import Optional, Any


DEFAULT_URL = "http://localhost:8765"
TIMEOUT = 60   # secondes (analyse NLP peut etre lente)


class RiskPulseError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}")


class RiskPulseClient:
    """Client SDK pour l'API RiskPulse."""

    def __init__(self, api_key: str, base_url: str = DEFAULT_URL):
        self.api_key  = api_key
        self.base_url = base_url.rstrip("/")

    # ── HTTP helper ──────────────────────────

    def _request(self, method: str, path: str, *,
                  json_body: Optional[dict] = None,
                  query: Optional[dict] = None,
                  timeout: int = TIMEOUT) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {
            "X-API-Key":   self.api_key,
            "Accept":      "application/json",
            "User-Agent":  "riskpulse-python-sdk/1.0",
        }
        data = None
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                if body:
                    return json.loads(body)
                return None
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err = json.loads(err_body).get("detail", err_body)
            except Exception:
                err = str(e)
            raise RiskPulseError(e.code, err)

    # ── Health & version ─────────────────────

    def health(self) -> dict:
        return self._request("GET", "/v1/health")

    def version(self) -> dict:
        return self._request("GET", "/v1/version")

    # ── Analyze ──────────────────────────────

    def analyze(self, text: str, language: str = "fr",
                 save_to_kb: bool = True) -> dict:
        """Lance une analyse complete et retourne le resultat structure."""
        return self._request("POST", "/v1/analyze", json_body={
            "text": text, "language": language, "save_to_kb": save_to_kb,
        }, timeout=120)

    # ── Entities ─────────────────────────────

    def list_entities(self, search: str = "", limit: int = 50) -> list[dict]:
        return self._request("GET", "/v1/entities",
                              query={"search": search, "limit": limit})

    def get_entity(self, entity_id: int) -> dict:
        return self._request("GET", f"/v1/entities/{entity_id}")

    def enrich_entity(self, entity_id: int, lang: str = "fr",
                       force: bool = False) -> dict:
        return self._request("POST", f"/v1/entities/{entity_id}/enrich",
                              query={"lang": lang, "force": str(force).lower()})

    # ── Watchlist ────────────────────────────

    def list_watches(self) -> list[dict]:
        return self._request("GET", "/v1/watchlist")

    def add_watch(self, name: str, threshold: float = 0.6, notes: str = "") -> dict:
        return self._request("POST", "/v1/watchlist", json_body={
            "name": name, "threshold": threshold, "notes": notes,
        })

    def remove_watch(self, watch_id: int) -> dict:
        return self._request("DELETE", f"/v1/watchlist/{watch_id}")

    # ── Sources ──────────────────────────────

    def list_sources(self) -> list[dict]:
        return self._request("GET", "/v1/sources")

    def add_source(self, url: str, label: str = "", source_type: str = "rss") -> dict:
        return self._request("POST", "/v1/sources", json_body={
            "url": url, "label": label, "type": source_type,
        })

    def run_monitoring(self) -> dict:
        return self._request("POST", "/v1/monitor/run", timeout=180)

    # ── Alerts ───────────────────────────────

    def list_alerts(self, unread_only: bool = False, limit: int = 50) -> list[dict]:
        return self._request("GET", "/v1/alerts",
                              query={"unread_only": str(unread_only).lower(),
                                     "limit": limit})

    def mark_all_seen(self) -> dict:
        return self._request("POST", "/v1/alerts/mark-all-seen")

    # ── Predictive ───────────────────────────

    def forecast(self, entity_id: int, horizon_days: int = 30) -> dict:
        return self._request("POST", "/v1/forecast", json_body={
            "entity_id": entity_id, "horizon_days": horizon_days,
        })

    def monte_carlo(self, n_runs: int = 1000, failure_prob: float = 0.15) -> dict:
        return self._request("POST", "/v1/monte-carlo", json_body={
            "n_runs": n_runs, "failure_prob": failure_prob,
        }, timeout=120)

    def trends(self, top_n: int = 20) -> list[dict]:
        return self._request("GET", "/v1/trends", query={"top_n": top_n})

"""
RiskPulse — Banking Pack
=========================
Couche de specialisation pour les usages bancaires / AML / KYC / compliance.

Composants :
  - Referentiels publics (FATF lists, regulateurs, banques connues, secteurs a risque)
  - Detection patterns bancaires (IBAN, BIC, LEI, montants multidevises)
  - BankingAnalyzer : post-process une analyse standard RiskPulse pour produire
    un profil AML par entite (flags + score AML composite)

Toutes les donnees sont publiques. Aucune base externe payante n'est requise.
"""

from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  REFERENTIELS PUBLICS
# ─────────────────────────────────────────────

# FATF — Pays soumis a "Increased Monitoring" ou "High-Risk Jurisdictions"
# Reference : https://www.fatf-gafi.org/ (juin 2024, sera a actualiser)
FATF_HIGH_RISK = {
    # Black list (Call for Action)
    "iran", "north korea", "coree du nord", "myanmar", "birmanie", "burma",
    # Grey list (Increased Monitoring) - extrait recent
    "syria", "syrie", "yemen", "south sudan", "soudan du sud",
    "haiti", "haïti", "burkina faso", "mali", "senegal", "south africa",
    "afrique du sud", "vietnam", "uganda", "ouganda", "tanzania", "tanzanie",
    "philippines", "nigeria", "monaco", "cameroon", "cameroun",
    "democratic republic of congo", "congo", "venezuela",
    "lebanon", "liban", "namibia", "namibie", "bulgaria", "bulgarie",
}

# Liste OFAC (extrait — pays sous sanctions US complettes)
OFAC_SANCTIONS_COUNTRIES = {
    "iran", "north korea", "cuba", "syria", "syrie", "russia", "russie",
    "belarus", "bielorussie", "venezuela", "myanmar", "birmanie",
    "crimea", "donetsk", "luhansk",
}

# Paradis fiscaux / juridictions a haut risque (liste UE + listes connues)
# Note : on N'INCLUT PAS la Suisse / le Luxembourg dans cette liste car ils sont
# sortis des grey lists UE depuis 2019 et ne sont plus consideres comme paradis
# fiscaux par les standards internationaux modernes. Les considerer comme tels
# generait trop de false positives sur des dossiers bancaires europeens normaux.
TAX_HAVENS = {
    "cayman islands", "iles caimans", "british virgin islands", "iles vierges",
    "bermuda", "bermudes", "panama", "bahamas", "vanuatu", "samoa",
    "marshall islands", "iles marshall", "anguilla", "barbados",
    "fiji", "fidji", "palau", "trinidad and tobago",
    "monaco", "liechtenstein", "andorra", "andorre", "isle of man",
    "jersey", "guernsey", "seychelles", "belize", "dominica",
}

# Top regulateurs financiers
REGULATORS = {
    # Multilateraux
    "fatf", "gafi", "bis", "bri", "iosco", "iaa",
    # Europe
    "ecb", "bce", "european central bank", "banque centrale europeenne",
    "eba", "european banking authority", "esma", "eiopa",
    "acpr", "amf", "autorite des marches financiers", "bafin", "consob",
    "fca", "financial conduct authority", "pra",
    # Amerique du Nord
    "fed", "federal reserve", "occ", "fdic", "finra", "sec",
    "ofac", "fincen", "cftc",
    # Maroc / Afrique
    "bank al-maghrib", "bam", "ammc",
    # Asie
    "pboc", "people's bank of china", "fsa japan", "mas", "hkma",
    # Suisse
    "finma", "snb", "swiss national bank",
}

# Top banques mondiales (extrait, non-exhaustif)
KNOWN_BANKS = {
    "jpmorgan", "jp morgan", "goldman sachs", "morgan stanley", "citigroup",
    "bank of america", "wells fargo", "hsbc", "barclays", "deutsche bank",
    "credit suisse", "ubs", "bnp paribas", "societe generale", "credit agricole",
    "santander", "bbva", "ing", "intesa sanpaolo", "unicredit",
    "lloyds", "natwest", "standard chartered", "rbc", "td bank",
    "icbc", "agricultural bank of china", "bank of china", "china construction bank",
    "mitsubishi ufj", "sumitomo mitsui", "mizuho",
    # Maroc
    "attijariwafa", "wafabank", "banque populaire", "bmce", "bank of africa",
    "cih", "credit du maroc", "societe generale maroc",
    # Banques centrales (regulateurs aussi)
    "bank al-maghrib", "bce", "fed", "boe", "boj", "pboc",
}

# Secteurs traditionnellement consideres a risque AML eleve
HIGH_RISK_SECTORS = {
    "crypto", "cryptocurrency", "cryptocurrencies", "blockchain",
    "casino", "casinos", "gambling", "betting", "paris en ligne",
    "money transfer", "transfert d'argent", "remittance",
    "real estate", "immobilier", "luxury goods", "luxe", "art",
    "diamond", "diamant", "precious metals", "metaux precieux",
    "cash-intensive", "espèces", "shell company", "société écran",
    "arms", "armement", "defense", "defence",
    "offshore", "trust", "fiducie", "private banking",
}

# Patterns reglementaires pour la detection
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b")
BIC_PATTERN  = re.compile(r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?\b")
LEI_PATTERN  = re.compile(r"\b[A-Z0-9]{18}\d{2}\b")
SWIFT_PATTERN= re.compile(r"\b[A-Z]{6}[A-Z0-9]{2,5}\b")


# Termes signalant potentiellement du blanchiment / structuration
LAUNDERING_TERMS = {
    "structuring", "structuration", "smurfing", "fractionnement",
    "layering", "stratification", "placement",
    "shell", "écran", "fictive", "fictif",
    "underground banking", "hawala", "fei chien",
    "trade-based", "transfert physique",
}

# Termes PEP indicators
PEP_INDICATORS = {
    "ministre", "minister", "president", "président",
    "ambassadeur", "ambassador", "deputy", "depute", "député",
    "senator", "senateur", "general", "général",
    "chief justice", "head of state", "prime minister", "premier ministre",
    "governor", "gouverneur", "central bank governor",
    "sovereign wealth", "fonds souverain",
    "royal family", "famille royale",
    "ruling party", "parti au pouvoir",
}


# ─────────────────────────────────────────────
#  STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class BankingFlag:
    """Un signal AML / KYC / compliance attache a une entite."""
    code:     str          # ex. 'FATF_HIGH_RISK', 'SANCTIONS', 'PEP'
    label:    str          # libelle court
    severity: str          # 'high' | 'medium' | 'low' | 'info'
    detail:   str = ""     # explication

    def to_dict(self) -> dict:
        return {"code": self.code, "label": self.label,
                "severity": self.severity, "detail": self.detail}


@dataclass
class BankingProfile:
    """Profil bancaire d'une entite."""
    node_id:        str
    name:           str
    category:       str = "entity"     # 'bank' | 'regulator' | 'jurisdiction' | 'entity' | 'person'
    flags:          list[BankingFlag] = field(default_factory=list)
    aml_score:      float = 0.0        # 0..1
    aml_verdict:    str = "CLEAR"      # CLEAR / LOW / MEDIUM / HIGH / CRITICAL
    sanctions_hit:  bool = False
    pep_indicator:  bool = False
    fatf_exposure:  bool = False
    tax_haven_link: bool = False

    def to_dict(self) -> dict:
        return {
            "node_id":        self.node_id,
            "name":           self.name,
            "category":       self.category,
            "flags":          [f.to_dict() for f in self.flags],
            "aml_score":      round(self.aml_score, 3),
            "aml_verdict":    self.aml_verdict,
            "sanctions_hit":  self.sanctions_hit,
            "pep_indicator":  self.pep_indicator,
            "fatf_exposure":  self.fatf_exposure,
            "tax_haven_link": self.tax_haven_link,
        }


# ─────────────────────────────────────────────
#  ANALYZER
# ─────────────────────────────────────────────

def _aml_verdict(score: float) -> str:
    if score >= 0.85: return "CRITICAL"
    if score >= 0.65: return "HIGH"
    if score >= 0.40: return "MEDIUM"
    if score >= 0.20: return "LOW"
    return "CLEAR"


class BankingAnalyzer:
    """
    Analyse une session RiskPulse sous l'angle AML / KYC / compliance.

    Entree : analysis dict (sortie de RiskController.analyze_text)
    Sortie : { profiles[], sectoral_metrics, regulatory_alerts, identifiers }
    """

    # Ponderation du score AML composite
    WEIGHTS = {
        "sanctions":   0.40,
        "fatf":        0.25,
        "pep":         0.15,
        "tax_haven":   0.10,
        "high_sector": 0.10,
    }

    def __init__(self, analysis: dict, source_text: str = ""):
        self.analysis = analysis
        self.entities = analysis.get("nlp", {}).get("entities", [])
        # Si on a le texte source, on l'utilise pour l'extraction des identifiants
        # (sinon, on retombe sur les phrases concatenees des entites)
        self.source_text = source_text or self._concat_sentences()
        self.text_full = self._concat_sentences()

    def _concat_sentences(self) -> str:
        chunks = []
        for e in self.entities:
            chunks.extend(e.get("sentences", []) or [])
        return "\n".join(chunks).lower()

    # ── Pipeline principal ──────────────────

    def analyze(self) -> dict:
        profiles: list[BankingProfile] = []
        for e in self.entities:
            profiles.append(self._profile_entity(e))

        identifiers = self._extract_identifiers()
        regulatory_alerts = self._detect_regulatory_alerts(profiles)
        sectoral = self._sectoral_metrics(profiles)

        return {
            "profiles":          [p.to_dict() for p in profiles],
            "identifiers":       identifiers,
            "regulatory_alerts": regulatory_alerts,
            "sectoral_metrics":  sectoral,
            "summary":           self._summary(profiles, identifiers, regulatory_alerts),
        }

    # ── Profil d'une entite ─────────────────

    def _profile_entity(self, ent: dict) -> BankingProfile:
        name = ent.get("name", "")
        node_id = ent.get("id", "")
        type_label = (ent.get("type_label") or "").lower()
        sentences = " ".join(ent.get("sentences", []) or []).lower()
        name_low = name.lower()

        flags: list[BankingFlag] = []
        category = "entity"
        sanctions_hit = False
        pep_indicator = False
        fatf_exposure = False
        tax_haven_link = False

        # ── Categorisation ──
        if any(b in name_low for b in KNOWN_BANKS):
            category = "bank"
            flags.append(BankingFlag(
                "REGULATED_BANK", "Banque regulee", "info",
                "Etablissement bancaire identifie dans le referentiel."
            ))
        elif any(r in name_low for r in REGULATORS):
            category = "regulator"
            flags.append(BankingFlag(
                "REGULATOR", "Autorite de regulation", "info",
                "Acteur supranational ou autorite de marche."
            ))
        elif "personne" in type_label or "person" in type_label:
            category = "person"
        elif "lieu" in type_label or "pays" in type_label or "country" in type_label:
            category = "jurisdiction"

        # ── Sanctions OFAC ──
        for s in OFAC_SANCTIONS_COUNTRIES:
            if s in name_low or f" {s} " in f" {sentences} ":
                sanctions_hit = True
                flags.append(BankingFlag(
                    "OFAC_SANCTIONS",
                    f"Pays sous sanctions ({s.title()})",
                    "high",
                    "Mention d'une juridiction figurant sur la liste OFAC."
                ))
                break

        # ── FATF grey/black list ──
        for f in FATF_HIGH_RISK:
            if f in name_low or f" {f} " in f" {sentences} ":
                fatf_exposure = True
                flags.append(BankingFlag(
                    "FATF_HIGH_RISK",
                    f"Juridiction FATF ({f.title()})",
                    "high",
                    "Pays sur la liste de surveillance FATF/GAFI."
                ))
                break

        # ── Paradis fiscaux ──
        for h in TAX_HAVENS:
            if h in name_low or f" {h} " in f" {sentences} ":
                tax_haven_link = True
                flags.append(BankingFlag(
                    "TAX_HAVEN",
                    f"Lien paradis fiscal ({h.title()})",
                    "medium",
                    "Mention d'une juridiction consideree comme paradis fiscal."
                ))
                break

        # ── PEP (Politically Exposed Person) ──
        if category == "person":
            for kw in PEP_INDICATORS:
                if kw in sentences or kw in name_low:
                    pep_indicator = True
                    flags.append(BankingFlag(
                        "PEP", "Personne politiquement exposee", "high",
                        f"Indicateur PEP detecte ({kw})."
                    ))
                    break

        # ── Secteurs a haut risque ──
        high_sector_hit = False
        for s in HIGH_RISK_SECTORS:
            if s in sentences or s in name_low:
                high_sector_hit = True
                flags.append(BankingFlag(
                    "HIGH_RISK_SECTOR", f"Secteur a risque ({s})", "medium",
                    "Activite dans un secteur considere a haut risque AML."
                ))
                break

        # ── Patterns de blanchiment ──
        for t in LAUNDERING_TERMS:
            if t in sentences:
                flags.append(BankingFlag(
                    "LAUNDERING_PATTERN", f"Pattern AML ({t})", "high",
                    f"Vocabulaire associe au blanchiment detecte ({t})."
                ))
                break

        # ── Score AML composite ──
        sub = {
            "sanctions":   1.0 if sanctions_hit else 0.0,
            "fatf":        1.0 if fatf_exposure else 0.0,
            "pep":         1.0 if pep_indicator else 0.0,
            "tax_haven":   1.0 if tax_haven_link else 0.0,
            "high_sector": 1.0 if high_sector_hit else 0.0,
        }
        aml_score = sum(self.WEIGHTS[k] * v for k, v in sub.items())
        aml_score = min(1.0, aml_score)

        return BankingProfile(
            node_id=node_id, name=name, category=category,
            flags=flags, aml_score=aml_score,
            aml_verdict=_aml_verdict(aml_score),
            sanctions_hit=sanctions_hit,
            pep_indicator=pep_indicator,
            fatf_exposure=fatf_exposure,
            tax_haven_link=tax_haven_link,
        )

    # ── Identifiants bancaires ──────────────

    def _extract_identifiers(self) -> dict:
        """Recherche IBAN, BIC, LEI dans le texte source de l'analyse."""
        text = self.source_text

        ibans = sorted(set(IBAN_PATTERN.findall(text)))
        # LEI : 20 caracteres exact
        leis  = sorted(set(LEI_PATTERN.findall(text)))
        leis  = [l for l in leis if len(l) == 20]

        # BIC : 8 ou 11 caracteres, en evitant les faux positifs
        # On exige que le mot precedent soit un indicateur ("BIC", "SWIFT", "code")
        bics = []
        for m in re.finditer(r"\b(SWIFT|BIC|CODE)[:\s]+([A-Z]{6}[A-Z0-9]{2,5})\b",
                              text, flags=re.IGNORECASE):
            bics.append(m.group(2))
        bics = sorted(set(bics))

        # Filtre les faux positifs IBAN
        ibans = [i for i in ibans if 14 <= len(i) <= 34
                  and not i.startswith(("UN", "QC", "QID"))]

        return {
            "iban":  ibans[:20],
            "bic":   bics[:20],
            "lei":   leis[:20],
        }

    # ── Alertes reglementaires ──────────────

    def _detect_regulatory_alerts(self, profiles: list[BankingProfile]) -> list[dict]:
        alerts = []
        # Concentration : >40% entites dans des juridictions FATF
        fatf_n = sum(1 for p in profiles if p.fatf_exposure)
        if profiles and fatf_n / len(profiles) > 0.4:
            alerts.append({
                "code": "FATF_CONCENTRATION",
                "severity": "high",
                "message": f"{fatf_n}/{len(profiles)} entites associees a des juridictions FATF ({fatf_n/len(profiles):.0%})",
            })

        # Sanctions
        sanc_n = sum(1 for p in profiles if p.sanctions_hit)
        if sanc_n > 0:
            alerts.append({
                "code": "SANCTIONS_HIT",
                "severity": "critical",
                "message": f"{sanc_n} entite(s) lie(es) a des juridictions sous sanctions",
            })

        # PEP
        pep_n = sum(1 for p in profiles if p.pep_indicator)
        if pep_n > 0:
            alerts.append({
                "code": "PEP_PRESENT",
                "severity": "high",
                "message": f"{pep_n} personne(s) politiquement exposee(s) identifiee(s)",
            })

        # Tax haven
        th_n = sum(1 for p in profiles if p.tax_haven_link)
        if th_n > 0:
            alerts.append({
                "code": "TAX_HAVEN_PRESENT",
                "severity": "medium",
                "message": f"{th_n} entite(s) liee(s) a un paradis fiscal",
            })

        # Termes-cles graves dans le texte global : escalation automatique
        # Une mention explicite de "detournement", "evasion fiscale", "fraude
        # comptable" doit elever le verdict, meme si pas d'entites flag-PEP/sanctions.
        FRAUD_KEYWORDS = {
            "detournement":       ("CLIENT_FUNDS_DIVERSION", "Detournement de fonds clients"),
            "commingling":        ("CLIENT_FUNDS_DIVERSION", "Comingling of client funds"),
            "evasion fiscale":    ("TAX_EVASION", "Schema d'evasion fiscale"),
            "fraude comptable":   ("ACCOUNTING_FRAUD", "Fraude comptable"),
            "accounting fraud":   ("ACCOUNTING_FRAUD", "Accounting fraud"),
            "schema ponzi":       ("PONZI_SCHEME", "Schema Ponzi suspecte"),
            "ponzi scheme":       ("PONZI_SCHEME", "Ponzi scheme suspected"),
            "blanchiment":        ("MONEY_LAUNDERING", "Vocabulaire de blanchiment"),
            "money laundering":   ("MONEY_LAUNDERING", "Money laundering vocabulary"),
            "transferts suspects":("SUSPICIOUS_TRANSFERS", "Transferts suspects mentionnes"),
            "suspicious transfer":("SUSPICIOUS_TRANSFERS", "Suspicious transfers mentioned"),
            "depose le bilan":    ("BANKRUPTCY", "Defaillance / faillite mentionnee"),
            "depot de bilan":     ("BANKRUPTCY", "Defaillance / faillite mentionnee"),
            "filed for bankruptcy":("BANKRUPTCY", "Bankruptcy mentioned"),
            "perte de confiance": ("CONFIDENCE_LOSS", "Perte de confiance des marches"),
            "loss of confidence": ("CONFIDENCE_LOSS", "Loss of market confidence"),
            "beneficiaire effectif": ("OPAQUE_OWNERSHIP", "Beneficial owner opacity"),
            "beneficial owner":   ("OPAQUE_OWNERSHIP", "Beneficial owner opacity"),
        }
        text_low = self.text_full
        for kw, (code, msg) in FRAUD_KEYWORDS.items():
            if kw in text_low:
                alerts.append({
                    "code":     code,
                    "severity": "high",
                    "message":  msg,
                })

        return alerts

    # ── Metriques sectorielles ──────────────

    def _sectoral_metrics(self, profiles: list[BankingProfile]) -> dict:
        if not profiles:
            return {}
        n = len(profiles)
        banks       = [p for p in profiles if p.category == "bank"]
        regulators  = [p for p in profiles if p.category == "regulator"]
        persons     = [p for p in profiles if p.category == "person"]
        jurisdic    = [p for p in profiles if p.category == "jurisdiction"]
        with_flags  = [p for p in profiles if p.flags]
        critical    = [p for p in profiles if p.aml_verdict in ("HIGH", "CRITICAL")]

        return {
            "n_total":       n,
            "n_banks":       len(banks),
            "n_regulators":  len(regulators),
            "n_persons":     len(persons),
            "n_jurisdictions": len(jurisdic),
            "n_flagged":     len(with_flags),
            "n_aml_critical":len(critical),
            "avg_aml":       round(sum(p.aml_score for p in profiles) / n, 3),
            "max_aml":       round(max(p.aml_score for p in profiles), 3),
        }

    # ── Summary ─────────────────────────────

    def _summary(self, profiles, identifiers, alerts) -> dict:
        critical_p = [p for p in profiles if p.aml_verdict == "CRITICAL"]
        high_p = [p for p in profiles if p.aml_verdict == "HIGH"]
        # Compte les alertes graves (high / critical)
        critical_alerts = [a for a in alerts if a["severity"] == "critical"]
        high_alerts = [a for a in alerts if a["severity"] == "high"]
        # ── Verdict escalade ──
        # Critical : sanctions, fraude comptable, Ponzi, money laundering explicite
        # High     : 2+ alertes high (PEP, FATF concentration, tax haven multi)
        # ou un single profile en HIGH/CRITICAL
        if critical_p or critical_alerts:
            verdict = "ESCALATION_REQUIRED"
        elif high_p or len(high_alerts) >= 2:
            verdict = "ENHANCED_DUE_DILIGENCE"
        elif high_alerts:
            verdict = "ENHANCED_DUE_DILIGENCE"
        else:
            verdict = "STANDARD_KYC"

        return {
            "headline_alerts": len(critical_alerts) + len(high_alerts),
            "n_critical":     len(critical_p),
            "n_high":         len(high_p),
            "n_identifiers":  sum(len(v) for v in identifiers.values()),
            "verdict":        verdict,
        }

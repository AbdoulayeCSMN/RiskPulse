"""
Pre-remplissage automatique des fichiers .ts via deep-translator.

Re-traite UNIQUEMENT les entrees dont la traduction == source (echec precedent).
"""

import sys
import time
import logging
from pathlib import Path
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


LANGS = ["fr", "en", "ar", "it", "es"]
LOCALES_DIR = Path(__file__).parent


def translate_one(text: str, target: str, retries: int = 3) -> tuple[str, bool]:
    """Retourne (translated_text, success_bool)."""
    if target == "en":
        return text, True
    from deep_translator import GoogleTranslator
    for attempt in range(retries):
        try:
            result = GoogleTranslator(source="en", target=target).translate(text)
            if result:
                return result, True
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            logger.warning(f"  ! [{target}] '{text[:50]}...' : {e}")
    return text, False


def process_ts(path: Path, target_lang: str, force: bool = False):
    logger.info(f"\n=== {path.name} (target: {target_lang}, force={force}) ===")
    tree = ET.parse(path)
    root = tree.getroot()
    root.set("language", f"{target_lang}_{target_lang.upper()}")

    total = 0
    translated = 0
    skipped = 0
    failed = 0

    for ctx in root.iter("context"):
        for msg in ctx.iter("message"):
            source_el = msg.find("source")
            trans_el = msg.find("translation")
            if source_el is None:
                continue
            total += 1
            source = (source_el.text or "").strip()
            existing = (trans_el.text or "").strip() if trans_el is not None else ""

            # Si force=True, retraite quand existing==source (echec precedent)
            # Sinon, retraite seulement si vide ou unfinished
            unfinished = trans_el is not None and trans_el.get("type") == "unfinished"
            needs_translation = (
                not existing
                or unfinished
                or (force and target_lang != "en" and existing == source)
            )

            if not needs_translation:
                skipped += 1
                continue

            new, ok = translate_one(source, target_lang)
            if trans_el is None:
                trans_el = ET.SubElement(msg, "translation")
            trans_el.text = new
            if "type" in trans_el.attrib:
                del trans_el.attrib["type"]
            if ok:
                translated += 1
            else:
                failed += 1

            # Delai genereux pour eviter le rate-limit Google
            if target_lang != "en":
                time.sleep(0.4)

    tree.write(path, encoding="utf-8", xml_declaration=True)
    logger.info(f"  total={total} translated={translated} skipped={skipped} failed={failed}")


def main():
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = args[0] if args else None
    for lang in LANGS:
        if only and lang != only:
            continue
        ts_path = LOCALES_DIR / f"riskpulse_{lang}.ts"
        if not ts_path.exists():
            logger.warning(f"Missing: {ts_path}")
            continue
        process_ts(ts_path, lang, force=force)


if __name__ == "__main__":
    main()

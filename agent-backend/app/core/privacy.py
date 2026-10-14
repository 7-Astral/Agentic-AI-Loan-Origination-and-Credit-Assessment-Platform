import re
from functools import lru_cache

from app.core.config import get_settings

ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "AU_TFN",
    "AU_ABN",
    "AU_ACN",
    "AU_MEDICARE",
    "AU_BSB",
    "BANK_ACCOUNT",
]

ENTITY_THRESHOLDS = {"PHONE_NUMBER": 0.4}

TOKEN = re.compile(r"<([A-Z_]+)_(\d+)>")


@lru_cache
def analyzer():
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.predefined_recognizers import (
        AuAbnRecognizer,
        AuAcnRecognizer,
        AuMedicareRecognizer,
        AuTfnRecognizer,
        PhoneRecognizer,
    )

    settings = get_settings()
    nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": settings.pii_spacy_model}],
        }
    ).create_engine()
    engine = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

    present = {e for r in engine.registry.recognizers for e in r.supported_entities}
    for recognizer in (AuTfnRecognizer(), AuAbnRecognizer(), AuAcnRecognizer(), AuMedicareRecognizer()):
        if not present.intersection(recognizer.supported_entities):
            engine.registry.add_recognizer(recognizer)
    engine.registry.remove_recognizer("PhoneRecognizer")
    engine.registry.add_recognizer(PhoneRecognizer(supported_regions=("AU", "NZ", "GB", "US")))
    engine.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="AU_BSB",
            patterns=[Pattern("au_bsb", r"\b\d{3}-?\d{3}\b", 0.3)],
            context=["bsb", "branch"],
        )
    )
    engine.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="BANK_ACCOUNT",
            patterns=[Pattern("au_account", r"\b\d{6,10}\b", 0.2)],
            context=["account", "acct", "acc"],
        )
    )
    return engine


def find(text: str) -> list:
    threshold = get_settings().pii_score_threshold
    results = analyzer().analyze(
        text=text,
        language="en",
        entities=ENTITIES,
        score_threshold=min([threshold, *ENTITY_THRESHOLDS.values()]),
    )
    results = [r for r in results if r.score >= ENTITY_THRESHOLDS.get(r.entity_type, threshold)]
    chosen = []
    for result in sorted(results, key=lambda r: (r.start, -(r.end - r.start), -r.score)):
        if chosen and result.start < chosen[-1].end:
            continue
        chosen.append(result)
    return chosen


def redact(text: str) -> str:
    if not text:
        return text
    out, cursor = [], 0
    for result in find(text):
        out.append(text[cursor:result.start])
        out.append(f"<{result.entity_type}>")
        cursor = result.end
    out.append(text[cursor:])
    return "".join(out)


class Pseudonymizer:
    def __init__(self) -> None:
        self._token_by_value: dict[tuple[str, str], str] = {}
        self._value_by_token: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def _token(self, entity: str, value: str) -> str:
        key = (entity, value)
        if key not in self._token_by_value:
            self._counts[entity] = self._counts.get(entity, 0) + 1
            token = f"<{entity}_{self._counts[entity]}>"
            self._token_by_value[key] = token
            self._value_by_token[token] = value
        return self._token_by_value[key]

    def mask(self, text: str) -> str:
        if not text:
            return text
        out, cursor = [], 0
        for result in find(text):
            out.append(text[cursor:result.start])
            out.append(self._token(result.entity_type, text[result.start:result.end]))
            cursor = result.end
        out.append(text[cursor:])
        return "".join(out)

    def restore(self, text: str) -> str:
        if not text or not self._value_by_token:
            return text
        return TOKEN.sub(lambda m: self._value_by_token.get(m.group(0), m.group(0)), text)

    @property
    def masked_count(self) -> int:
        return len(self._value_by_token)

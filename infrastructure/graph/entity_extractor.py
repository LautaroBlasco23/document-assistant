import json
import logging
import re

from core.ports.llm import LLM

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Extract named entities from the text.
Return ONLY a JSON array. Each element must have:
  "name": string
  "type": one of Person, Place, Org, Event, Concept
  "context": brief phrase showing how it's used

Example: [{"name":"Alan Turing","type":"Person","context":"invented the Turing test"}]
Return [] if no entities found."""

# Fallback regex for capitalized proper nouns (two consecutive capitalized words)
_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")


def extract_entities(text: str, llm: LLM) -> list[dict]:
    """
    Extract named entities from text using the LLM.
    Falls back to regex extraction if the LLM returns unparseable output.
    """
    # Truncate to ~2000 words to keep prompt manageable
    words = text.split()
    truncated = " ".join(words[:2000])

    try:
        raw = _call_llm(truncated, llm)
        entities = _parse_json(raw)
        if entities is not None:
            logger.debug("Extracted %d entities via LLM", len(entities))
            return entities
    except Exception as exc:
        logger.warning("LLM entity extraction failed: %s", exc)

    # Regex fallback
    matches = _PROPER_NOUN_RE.findall(truncated)
    seen: set[str] = set()
    entities = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            entities.append({"name": m, "type": "Concept", "context": ""})
    logger.debug("Extracted %d entities via regex fallback", len(entities))
    return entities


def _call_llm(text: str, llm: LLM) -> str:
    # Use chat if available, otherwise generate
    if hasattr(llm, "chat"):
        return llm.chat(_SYSTEM_PROMPT, text)
    prompt = f"{_SYSTEM_PROMPT}\n\nText:\n{text}\n\nEntities:"
    return llm.generate(prompt)


def _parse_json(raw: str) -> list[dict] | None:
    """Try to extract a JSON array from a possibly-noisy LLM response."""
    raw = raw.strip()
    # Find first '[' and last ']'
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(raw[start : end + 1])
        if isinstance(data, list):
            return [e for e in data if isinstance(e, dict) and "name" in e]
    except json.JSONDecodeError:
        pass
    return None

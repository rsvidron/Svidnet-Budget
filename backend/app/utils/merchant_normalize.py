"""
Merchant name normalization.

Goal: collapse PNC-style variants like
    "LOWE'S 22 BETHEL PARK PA POS PURCHASE POS001 XXX31"
    "LOWE'S 22 BETHEL PARK PA POS PURCHASE POS001 XXX22"
    "DEBIT CARD PURCHASE XXXXXXXXXXXXXXXX5580 LOWES X09"
into a single grouping key like "lowes".

The normalized value is the *grouping key*, not a display name. The UI keeps
showing the raw merchant string and uses the most common raw string as the
group title.
"""
from __future__ import annotations
import re

# Order matters in some patterns; each is applied in sequence.
_DEBIT_CARD_PREFIX = re.compile(r"^\s*debit\s+card\s+purchase\s+x+\d*\s*", re.IGNORECASE)
_POS_PURCHASE_RUN = re.compile(r"\b(pos\s*\d*|purchase|debit|credit|withdrawal|payment|store|stores|mkt|market|center|ctr)\b", re.IGNORECASE)
_TRAILING_X_TOKEN = re.compile(r"\bxxx\d+\b|\bx\d+\b", re.IGNORECASE)
_TRAILING_ID = re.compile(r"\b\d{3,}\b")
_STORE_NUM_HASH = re.compile(r"#\d+")
# US state code at end of phrase like "BETHEL PARK PA"
_TRAILING_STATE = re.compile(r"\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b", re.IGNORECASE)
_NON_ALNUM_RUN = re.compile(r"[^a-z0-9]+")
_PUNCT_TO_SPACE = re.compile(r"['`*.,/\\\-_:;()\[\]{}!|]+")


def normalize_merchant(raw: str | None) -> str:
    """Return a stable grouping key for a merchant string.

    Empty / None input returns an empty string — callers should treat that as
    "no group" and fall back to the raw value.
    """
    if not raw:
        return ""
    s = raw.strip()
    if not s:
        return ""

    # Strip the PNC debit-card prefix ("DEBIT CARD PURCHASE XXXXXXXXXXXXXXXX5580 ...")
    s = _DEBIT_CARD_PREFIX.sub("", s)

    # Lowercase before tokenizing — comparisons later are case-insensitive.
    s = s.lower()

    # Drop store numbers like "#1234" and POS/purchase noise tokens.
    s = _STORE_NUM_HASH.sub(" ", s)
    s = _POS_PURCHASE_RUN.sub(" ", s)

    # Drop trailing-ish "XXX##" / "X09" placeholder tokens.
    s = _TRAILING_X_TOKEN.sub(" ", s)

    # Replace punctuation that often joins tokens with spaces (apostrophes etc).
    s = _PUNCT_TO_SPACE.sub(" ", s)

    # Tokenize. Drop:
    #  - pure numeric tokens (store IDs, suffix numbers)
    #  - 2-letter US state codes
    #  - empty tokens
    raw_tokens = [t for t in s.split() if t]
    tokens: list[str] = []
    for t in raw_tokens:
        if t.isdigit():
            continue
        if _TRAILING_STATE.fullmatch(t):
            continue
        # mostly-digit token (e.g. "5580", "00123") — drop
        if sum(c.isdigit() for c in t) >= max(2, len(t) - 1):
            continue
        tokens.append(t)

    if not tokens:
        # Fall back to a slug of the raw lowercased string to avoid empty key.
        return _NON_ALNUM_RUN.sub("", raw.lower())[:40]

    # Keep the first 1-2 meaningful tokens — enough to disambiguate brands
    # ("whole foods", "trader joe") without dragging in city/state/IDs.
    head = tokens[:2]
    # Collapse to a single key — letters+digits only.
    key = "".join(head)
    key = _NON_ALNUM_RUN.sub("", key)
    return key[:64]

"""Small, dependency-free normalization helpers shared across services."""
from __future__ import annotations

import re
import unicodedata


def normalize_header(raw: str) -> str:
    """Turn any header spelling into a comparable slug.

    'Created On', 'created_on', 'CREATED-ON', ' Created   On ' all become
    'created on' -> used as the lookup key against config.COLUMN_ALIASES.
    """
    if raw is None:
        return ""
    s = unicodedata.normalize("NFKD", str(raw))
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def normalize_token(raw) -> str:
    """Normalize a categorical value (status/priority/category) for matching:
    upper-case, whitespace/hyphen/space collapsed to single underscore.
    Keeps values like 'IN_PROGRESS' and 'In Progress' equal.
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return ""
    s = re.sub(r"[\s\-/]+", "_", s.strip())
    return s.upper()


def title_case_label(token: str) -> str:
    """Best-effort human label for a normalized token, e.g. IN_PROGRESS -> In Progress."""
    if not token:
        return ""
    return " ".join(w.capitalize() for w in token.split("_"))

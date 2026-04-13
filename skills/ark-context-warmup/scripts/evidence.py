"""Evidence candidate generator per spec D3."""
import re

# Trigger phrases for prior-rejection detection (per D3)
_REJECTION_TRIGGERS = [
    "decided against",
    "tried and failed",
    "rejected",
    "won't do",
    "wont do",
    "abandoned",
]


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _tokenize_for_trigger(s: str) -> list:
    """Tokenize for rejection-trigger matching. Strip apostrophes so quotes
    containing 'won't' produce the same tokens ('wont') as the trigger list
    after apostrophe removal. Without this, the natural spelling 'won't do'
    never matched and codex P2 flagged it as an unreachable trigger branch."""
    return re.findall(r"[a-zA-Z0-9]+", s.lower().replace("'", "").replace("\u2019", ""))


def _has_trigger_near_keywords(quote: str, task_tokens: set, window: int = 30) -> bool:
    """True if any trigger phrase occurs within `window` tokens of ≥2 task tokens."""
    words = _tokenize_for_trigger(quote)
    for trigger in _REJECTION_TRIGGERS:
        trig_words = _tokenize_for_trigger(trigger)
        if not trig_words:
            continue
        for i in range(len(words) - len(trig_words) + 1):
            if words[i:i + len(trig_words)] == trig_words:
                start = max(0, i - window)
                end = min(len(words), i + len(trig_words) + window)
                win_tokens = set(words[start:end])
                if len(win_tokens & task_tokens) >= 2:
                    return True
    return False


def derive_candidates(*, task_normalized, scenario, tasknotes, notebooklm, wiki):
    """Returns a list of evidence candidates per spec D3.

    Each candidate: {type, confidence?, id?, detail, reason}

    Lane argument semantics:
      - None  → lane was unavailable; emits a Degraded coverage candidate
      - dict  → lane ran (possibly returning empty content); does NOT emit Degraded coverage
    """
    out = []

    # Duplicate + in-flight collision (from tasknotes)
    if tasknotes is not None:
        extracted_component = tasknotes.get("extracted_component", "")
        for m in tasknotes.get("matches", []):
            if m["status"] == "done":
                continue
            # Duplicate
            dup_conf = None
            matched = m.get("matched_field") or ""
            if matched == "component" and m.get("status") in ("in-progress", "open", "planned"):
                dup_conf = "high"
            elif matched and matched.startswith("title_overlap="):
                overlap = float(matched.split("=", 1)[1])
                if overlap >= 0.60:
                    dup_conf = "medium"
                # <0.60 -> dropped
            if dup_conf:
                out.append({
                    "type": "Possible duplicate",
                    "confidence": dup_conf,
                    "id": m["id"],
                    "detail": m["title"],
                    "reason": f"matched {matched}; status={m['status']}",
                })
            # In-flight collision (distinct signal from duplicate)
            if m.get("status") == "in-progress":
                if extracted_component and m.get("component", "").lower() == extracted_component:
                    out.append({
                        "type": "Possible in-flight collision",
                        "confidence": "high",
                        "id": m["id"],
                        "detail": m["title"],
                        "reason": f"shared component={extracted_component}; status=in-progress",
                    })
    else:
        out.append({
            "type": "Degraded coverage",
            "detail": "tasknotes lane unavailable",
            "reason": "backend skipped per availability probe",
        })

    # Prior rejection (from notebooklm citations)
    task_tokens = _tokens(task_normalized)
    if notebooklm is not None:
        for cit in (notebooklm.get("citations") or []):
            quote = cit.get("quote", "")
            if _has_trigger_near_keywords(quote, task_tokens):
                out.append({
                    "type": "Possible prior rejection",
                    "confidence": "medium",
                    "id": cit.get("session", ""),
                    "detail": quote,
                    "reason": "trigger phrase within 30 tokens of ≥2 task keywords",
                })
    else:
        out.append({
            "type": "Degraded coverage",
            "detail": "notebooklm lane unavailable",
            "reason": "backend skipped per availability probe",
        })

    # Wiki: only emit Degraded coverage if the lane itself was unavailable
    if wiki is None:
        out.append({
            "type": "Degraded coverage",
            "detail": "wiki lane unavailable",
            "reason": "backend skipped per availability probe",
        })
    # If wiki is a dict (even with empty matches), this is a legitimate result — no Degraded coverage.

    return out

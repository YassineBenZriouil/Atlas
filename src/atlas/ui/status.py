"""Maps AtlasState names to tray-facing text (Atlas.md section 68: the user
must always know whether ATLAS is listening)."""

from __future__ import annotations

_STATUS_LABELS: dict[str, str] = {
    "SLEEPING": "Status: Sleeping",
    "WAKE_DETECTED": "Status: Waking...",
    "LISTENING": "Status: Listening",
    "RECOGNIZING": "Status: Recognizing...",
    "PARSING": "Status: Thinking...",
    "VALIDATING": "Status: Validating...",
    "EXECUTING": "Status: Executing...",
    "FEEDBACK": "Status: Done",
    "ERROR": "Status: Error",
    "RECOVERY": "Status: Recovering...",
    "DISABLED": "Status: Disabled",
}


def status_text(state_name: str) -> str:
    return _STATUS_LABELS.get(state_name, f"Status: {state_name}")

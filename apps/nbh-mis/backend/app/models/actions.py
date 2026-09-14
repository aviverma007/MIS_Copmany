"""Management Action Tracker -- simple JSON-file-backed CRUD store.

Per the prompt this can "initially be manually editable in the UI"; a JSON
file keeps it durable across backend restarts without needing a database,
while staying trivial to swap for a real table later.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import date, datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
ACTIONS_FILE = os.path.join(DATA_DIR, "actions.json")

VALID_STATUSES = ["Open", "In Progress", "Closed", "Overdue"]

_lock = threading.Lock()


def _ensure_store():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ACTIONS_FILE):
        with open(ACTIONS_FILE, "w") as f:
            json.dump([], f)


def _load() -> list[dict]:
    _ensure_store()
    with open(ACTIONS_FILE) as f:
        actions = json.load(f)
    today = date.today().isoformat()
    changed = False
    for a in actions:
        if a["status"] not in ("Closed",) and a.get("target_date") and a["target_date"] < today and a["status"] != "Overdue":
            a["status"] = "Overdue"
            changed = True
    if changed:
        _save(actions)
    return actions


def _save(actions: list[dict]):
    with open(ACTIONS_FILE, "w") as f:
        json.dump(actions, f, indent=2, default=str)


def list_actions() -> list[dict]:
    with _lock:
        return _load()


def add_action(title: str, owner: str, target_date: str, status: str = "Open") -> dict:
    with _lock:
        actions = _load()
        action = {
            "id": str(uuid.uuid4()),
            "title": title,
            "owner": owner,
            "target_date": target_date,
            "status": status if status in VALID_STATUSES else "Open",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        actions.append(action)
        _save(actions)
        return action


def update_action(action_id: str, **fields) -> dict | None:
    with _lock:
        actions = _load()
        for a in actions:
            if a["id"] == action_id:
                for k, v in fields.items():
                    if v is not None:
                        a[k] = v
                _save(actions)
                return a
        return None


def delete_action(action_id: str) -> bool:
    with _lock:
        actions = _load()
        new_actions = [a for a in actions if a["id"] != action_id]
        if len(new_actions) == len(actions):
            return False
        _save(new_actions)
        return True

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import actions as actions_model
from app.schemas.actions import ActionCreate, ActionUpdate

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("")
def list_actions():
    return {"actions": actions_model.list_actions()}


@router.post("")
def create_action(payload: ActionCreate):
    if payload.status not in actions_model.VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {actions_model.VALID_STATUSES}")
    return actions_model.add_action(payload.title, payload.owner, payload.target_date, payload.status)


@router.put("/{action_id}")
def update_action(action_id: str, payload: ActionUpdate):
    if payload.status and payload.status not in actions_model.VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {actions_model.VALID_STATUSES}")
    result = actions_model.update_action(action_id, **payload.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=404, detail="Action not found.")
    return result


@router.delete("/{action_id}")
def delete_action(action_id: str):
    ok = actions_model.delete_action(action_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Action not found.")
    return {"message": "deleted"}

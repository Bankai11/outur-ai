"""API router for webhooks (Resend email tracking)."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from core.models.outreach_draft import OutreachDraft
from core.logger import get_logger

log = get_logger(__name__)
router = APIRouter()

@router.post("/resend", status_code=status.HTTP_200_OK)
async def resend_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Receive webhook events from Resend for email status tracking.
    Valid events: email.sent, email.delivered, email.opened, email.bounced, etc.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type")
    data = payload.get("data", {})
    email_id = data.get("email_id")
    
    if not event_type or not email_id:
        return {"status": "ignored"}
        
    log.info("Received Resend webhook", event_type=event_type, email_id=email_id)

    # Map resend events to our status string
    status_map = {
        "email.sent": "sent",
        "email.delivered": "delivered",
        "email.opened": "opened",
        "email.bounced": "bounced",
        "email.clicked": "clicked",
        "email.complained": "complained"
    }
    
    new_status = status_map.get(event_type)
    if not new_status:
        return {"status": "ignored"}

    # Update database
    stmt = select(OutreachDraft).where(OutreachDraft.external_id == email_id)
    res = await session.execute(stmt)
    draft = res.scalars().first()
    
    if draft:
        draft.status = new_status
        await session.commit()
        log.info("Updated draft status via webhook", draft_id=str(draft.id), status=new_status)
    else:
        log.warning("Received webhook for unknown email_id", email_id=email_id)

    return {"status": "success"}


@router.post("/inbound", status_code=status.HTTP_200_OK)
async def inbound_email_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Receive inbound email replies. 
    Routes the raw reply text through an LLM to classify it into discrete categories.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # This could adapt to a specific provider's payload structure
    original_email_id = payload.get("original_email_id")
    reply_text = payload.get("text", "")
    
    if not original_email_id or not reply_text:
        return {"status": "ignored", "reason": "Missing original_email_id or text"}

    stmt = select(OutreachDraft).where(OutreachDraft.external_id == original_email_id)
    res = await session.execute(stmt)
    draft = res.scalars().first()

    if not draft:
        log.warning("Received reply for unknown email_id", email_id=original_email_id)
        return {"status": "ignored", "reason": "Unknown email_id"}

    from datetime import datetime
    draft.reply_received_at = datetime.utcnow()

    # Reply Classification using LLM
    from core.llm import get_llm_provider
    llm = get_llm_provider()
    
    prompt = f"""
    Analyze the following email reply and classify the prospect's intent.
    Choose exactly one of the following categories:
    - Interested
    - Book Meeting
    - Not Interested
    - Wrong Person
    - Come Back Later
    - Pricing Question
    - Forwarded
    - Spam
    - Out of Office

    Reply Text:
    \"\"\"{reply_text}\"\"\"

    Output a JSON object with a single field 'status' containing the exact category name.
    """
    
    classification_schema = {
        "type": "OBJECT",
        "properties": {
            "status": {"type": "STRING"}
        },
        "required": ["status"]
    }

    classification = await llm.generate_json(prompt, classification_schema)
    if classification and "status" in classification:
        draft.reply_status = classification["status"]
        log.info("Classified email reply", email_id=original_email_id, status=draft.reply_status)
    else:
        log.warning("Failed to classify reply, falling back to None", email_id=original_email_id)
        draft.reply_status = None

    await session.commit()
    return {"status": "processed", "classification": draft.reply_status}

"""Manual Campaign Approval CLI."""
import asyncio
import uuid
import sys
import os
import argparse
from sqlalchemy import select

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.engine import async_session_factory
from core.models.campaign import Campaign
from core.models.outreach_draft import OutreachDraft
from core.models.contact import Contact

async def approve_campaign_drafts(campaign_id: str, action: str):
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        print("Invalid campaign ID format. Must be a UUID.")
        return
        
    async with async_session_factory() as session:
        campaign = await session.get(Campaign, cid)
        if not campaign:
            print(f"Campaign {cid} not found.")
            return

        stmt = select(OutreachDraft, Contact).join(Contact, OutreachDraft.contact_id == Contact.id).where(
            OutreachDraft.campaign_id == cid,
            OutreachDraft.status == "draft"
        )
        res = await session.execute(stmt)
        drafts = res.all()

        if not drafts:
            print("No pending drafts found for this campaign.")
            return

        if action == "all":
            print(f"Approving all {len(drafts)} drafts...")
            for draft, _ in drafts:
                draft.approval_status = "approved"
                session.add(draft)
        elif action == "selected":
            print(f"Found {len(drafts)} drafts. Approving selected is not fully implemented in CLI. Interactive mode needed.")
            return
        elif action == "reject":
            print(f"Rejecting all {len(drafts)} drafts...")
            for draft, _ in drafts:
                draft.approval_status = "rejected"
                session.add(draft)
                
        await session.commit()
        print("Done. You can now execute the campaign.")

def main():
    parser = argparse.ArgumentParser(description="Approve campaign drafts manually.")
    parser.add_argument("campaign_id", type=str, help="UUID of the campaign")
    parser.add_argument("--action", type=str, choices=["all", "reject"], default="all", help="Action to take")
    args = parser.parse_args()
    
    asyncio.run(approve_campaign_drafts(args.campaign_id, args.action))

if __name__ == "__main__":
    main()

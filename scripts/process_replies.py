"""
Process Replies Script

Simulates the processing of incoming email replies to test the ReplyClassifierAgent.
Takes a set of sample replies and outputs the resulting classifications.
"""

import os
os.environ["APP_ENV"] = "testing"

import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from agents.reply_classifier import ReplyClassifierAgent

console = Console()

# Mock data to simulate replies to our outreach
MOCK_REPLIES = [
    {
        "prospect_name": "Sarah",
        "company_name": "TechFlow",
        "original_email": "Hi Sarah, noticed TechFlow has grown by 50 employees this quarter. Are you dealing with onboarding chaos? Our platform can automate that.",
        "reply_text": "Thanks for reaching out. We actually just signed a 2-year contract with CultureAmp for this. Not looking to change right now."
    },
    {
        "prospect_name": "David",
        "company_name": "CloudScale",
        "original_email": "David, saw you just raised a Series B. Managing hybrid work for a growing team is tough. Can KultrXP help?",
        "reply_text": "Timing is pretty good actually. Do you integrate with Slack? If so, I could chat next Tuesday afternoon."
    },
    {
        "prospect_name": "Elena",
        "company_name": "FinTrust",
        "original_email": "Elena, how is FinTrust managing compliance training tracking? KultrXP can streamline it.",
        "reply_text": "Please remove me from your list."
    },
    {
        "prospect_name": "Marcus",
        "company_name": "DevWorks",
        "original_email": "Marcus, I saw DevWorks is opening a new office in Austin. KultrXP helps distributed teams stay connected.",
        "reply_text": "I'm not the right person for this. You probably want to speak with our Head of People Ops, Jessica."
    },
    {
        "prospect_name": "Lisa",
        "company_name": "HealthPlus",
        "original_email": "Lisa, our platform helps reduce employee turnover by 30%.",
        "reply_text": "Looks interesting but we just don't have the budget for new HR tools this year. Maybe reach back out in Q3."
    }
]

async def main():
    console.print("[bold blue]Starting Reply Processing Simulation...[/bold blue]\n")
    
    agent = ReplyClassifierAgent()

    table = Table(title="Reply Classifications", show_header=True, header_style="bold magenta")
    table.add_column("Company")
    table.add_column("Reply Snippet", style="dim", max_width=40)
    table.add_column("Classification", style="cyan")
    table.add_column("Positive?", justify="center")
    table.add_column("Objection/Competitor", max_width=30)
    
    for item in MOCK_REPLIES:
        console.print(f"Processing reply from {item['prospect_name']} at {item['company_name']}...")
        
        result = await agent.run(
            reply_text=item["reply_text"],
            original_email=item["original_email"],
            prospect_name=item["prospect_name"],
            company_name=item["company_name"]
        )
        
        if result["success"]:
            data = result["data"]
            
            snippet = item["reply_text"][:37] + "..." if len(item["reply_text"]) > 40 else item["reply_text"]
            
            objection = data.get("objection_identified", "")
            competitor = data.get("competitor_mentioned", "")
            
            issues = []
            if objection: issues.append(objection)
            if competitor: issues.append(f"Competitor: {competitor}")
            
            table.add_row(
                item["company_name"],
                snippet,
                data.get("classification", "Unknown"),
                "Yes" if data.get("is_positive") else "No",
                " | ".join(issues)
            )
        else:
            console.print(f"[red]Error processing reply:[/red] {result['errors']}")
            
    console.print("\n")
    console.print(table)
    
if __name__ == "__main__":
    asyncio.run(main())

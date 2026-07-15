import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
import time

console = Console()

def run_review():
    """
    Review drafted emails pending approval.
    """
    console.print("\n[bold blue]📝 Review Drafts[/bold blue]\n")
    
    # Mocking fetching a draft
    console.print("Fetching drafts...\n")
    time.sleep(1)
    
    draft = """Subject: Optimizing hiring at Acme Corp
    
Hi John,

Noticed Acme Corp is rapidly expanding its engineering team. Usually that means growing pains with onboarding and aligning culture.

Kultrp helps mid-market tech companies scale their engineering culture without losing their core identity.

Open to a quick chat next week?

Best,
Outur AI
"""
    
    console.print(Panel(draft, title="Draft 1 of 30: Acme Corp", border_style="cyan"))
    
    if Confirm.ask("Approve this draft?"):
        console.print("[green]✓ Approved.[/green]")
    else:
        console.print("[red]✗ Rejected.[/red]")
        
    console.print("\nTo review all, you can use the web interface or continue here.")

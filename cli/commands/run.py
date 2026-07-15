import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
import time
import asyncio
from pydantic import BaseModel, Field

console = Console()

class CampaignSpec(BaseModel):
    industry: str | None = None
    country: str | None = None
    employee_size: str | None = None
    buyer: str | None = None
    signals: str | None = None
    limit: int = 10
    tone: str = "Professional"
    playbook: str | None = None

def run_campaign():
    """
    Launch a new campaign using natural language.
    """
    console.print("\n[bold blue]🚀 Launch Campaign[/bold blue]\n")
    
    prompt = Prompt.ask("Describe the campaign you want to run")
    
    with console.status("Parsing your request using Outur LLM..."):
        # TODO: Call Gemini to parse prompt into CampaignSpec
        # For now, mock it:
        time.sleep(1.5)
        spec = CampaignSpec(
            industry="SaaS",
            country="India",
            employee_size="50-300",
            buyer="HR Manager",
            signals="Hiring",
            limit=30,
            tone="Professional",
            playbook="Growth"
        )
    
    console.print("\n[bold]I understood:[/bold]")
    console.print(f"Industry:      [cyan]{spec.industry}[/cyan]")
    console.print(f"Country:       [cyan]{spec.country}[/cyan]")
    console.print(f"Company Size:  [cyan]{spec.employee_size}[/cyan]")
    console.print(f"Buyer:         [cyan]{spec.buyer}[/cyan]")
    console.print(f"Signals:       [cyan]{spec.signals}[/cyan]")
    console.print(f"Campaign Size: [cyan]{spec.limit}[/cyan]")
    console.print(f"Tone:          [cyan]{spec.tone}[/cyan]")
    console.print(f"Playbook:      [cyan]{spec.playbook}[/cyan]\n")
    
    if not Confirm.ask("Proceed?"):
        console.print("Cancelled.")
        return
        
    console.print("")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=False,
    ) as progress:
        task1 = progress.add_task("[cyan]Finding companies...", total=None)
        time.sleep(2)
        progress.update(task1, description="[green]✓ Found 30 companies")
        
        task2 = progress.add_task("[cyan]Researching prospects...", total=None)
        time.sleep(2)
        progress.update(task2, description="[green]✓ Researched 30 prospects")
        
        task3 = progress.add_task("[cyan]Generating sales intelligence...", total=None)
        time.sleep(2)
        progress.update(task3, description="[green]✓ Generated sales intelligence")
        
        task4 = progress.add_task("[cyan]Writing emails...", total=None)
        time.sleep(2)
        progress.update(task4, description="[green]✓ Wrote 30 emails")
        
        task5 = progress.add_task("[cyan]QA Review...", total=None)
        time.sleep(2)
        progress.update(task5, description="[green]✓ QA Review complete")
        
    console.print("\n[bold green]Done.[/bold green]")
    console.print("You can review the drafts using: [bold cyan]outur review[/bold cyan]\n")

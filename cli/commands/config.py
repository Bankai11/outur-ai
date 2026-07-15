import typer
from rich.console import Console
from rich.table import Table
import os

console = Console()

def run_config():
    """
    View or update current Outur AI configuration.
    """
    console.print("\n[bold blue]⚙️ Outur AI Configuration[/bold blue]\n")
    
    # In a real app we'd load this from business.yaml or .env
    # For now we'll mock it based on what was likely set
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting")
    table.add_column("Value")
    
    table.add_row("Company Name", "Kultrp")
    table.add_row("Website", "https://kultrp.com")
    table.add_row("ICP", "Mid-market B2B tech companies")
    table.add_row("Tone", "Professional")
    
    console.print(table)
    console.print("\nTo update these settings, edit [bold cyan]business.yaml[/bold cyan] or run [bold cyan]outur init[/bold cyan] again.\n")

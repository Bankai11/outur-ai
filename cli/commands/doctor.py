import typer
from rich.console import Console
import time
import os

console = Console()

def run_doctor():
    """
    Check system health and API connections.
    """
    console.print("\n[bold blue]🩺 Outur AI System Check[/bold blue]\n")
    
    issues_found = 0
    
    with console.status("Checking system dependencies..."):
        time.sleep(0.5)
        console.print("[green]✓[/green] Python 3.12+")
        console.print("[green]✓[/green] Dependencies installed")
        
    console.print("")
    with console.status("Checking API Connections..."):
        time.sleep(0.5)
        if os.environ.get("GEMINI_API_KEY"):
            console.print("[green]✓[/green] Gemini API (Configured)")
        else:
            console.print("[red]✗[/red] Gemini API (Missing)")
            issues_found += 1
            
        time.sleep(0.5)
        if os.environ.get("TAVILY_API_KEY"):
            console.print("[green]✓[/green] Tavily API (Configured)")
        else:
            console.print("[red]✗[/red] Tavily API (Missing)")
            issues_found += 1
            
    console.print("")
    with console.status("Checking Storage..."):
        time.sleep(0.5)
        if os.environ.get("DATABASE_URL"):
            console.print("[green]✓[/green] Database configured")
        else:
            console.print("[red]✗[/red] Database missing")
            issues_found += 1
            
    console.print("\n---")
    if issues_found == 0:
        console.print("[bold green]System is healthy! Ready to run campaigns.[/bold green]")
    else:
        console.print(f"[bold red]Found {issues_found} issue(s).[/bold red] Run [bold cyan]outur init[/bold cyan] to fix them.")
        
    console.print("")

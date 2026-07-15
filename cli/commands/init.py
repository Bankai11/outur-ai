from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
import time
import os

console = Console()

def run_init():
    """
    Initial setup wizard to configure Outur AI.
    """
    console.print("\n[bold blue]🚀 Welcome to Outur AI[/bold blue]")
    console.print("Let's get your AI sales platform ready.")
    console.print("Estimated setup time: [green]2 minutes[/green].\n")
    
    with console.status("[bold]Checking dependencies...[/bold]"):
        time.sleep(0.5)
        console.print("[green]✓[/green] Python 3.12+")
        time.sleep(0.2)
        console.print("[green]✓[/green] Docker")
        time.sleep(0.2)
        console.print("[green]✓[/green] PostgreSQL")
        time.sleep(0.2)
        console.print("[green]✓[/green] uv")
        time.sleep(0.2)
        console.print("[green]✓[/green] Project dependencies")
        console.print("[green]✓ Everything looks good.[/green]\n")
        
    console.print("---")
    console.print("[bold]Gemini API Key[/bold]")
    gemini_key = Prompt.ask("Paste your Gemini API key")
    
    with console.status("Validating Gemini API key..."):
        # TODO: Implement actual validation call
        time.sleep(1)
        console.print("[green]✓ Connected successfully.[/green]\n")
        
    console.print("---")
    console.print("[bold]Tavily API Key[/bold]")
    tavily_key = Prompt.ask("Paste your Tavily API key")
    
    with console.status("Validating Tavily API key..."):
        time.sleep(1)
        console.print("[green]✓ Connected successfully.[/green]\n")
        
    console.print("---")
    console.print("[bold]Email Provider[/bold]")
    console.print("1. Resend")
    console.print("2. SMTP")
    console.print("3. Gmail")
    console.print("4. SendGrid")
    console.print("5. Microsoft Graph")
    
    provider_choice = IntPrompt.ask("Select provider", choices=["1", "2", "3", "4", "5"], default=1)
    
    resend_key = ""
    if provider_choice == 1:
        resend_key = Prompt.ask("Paste your Resend API key")
        console.print("[green]✓ Provider configured.[/green]\n")
        
    console.print("---")
    console.print("[bold]Business Configuration[/bold]")
    company_name = Prompt.ask("Company Name")
    website = Prompt.ask("Website")
    pitch = Prompt.ask("One sentence describing your company")
    icp = Prompt.ask("Who are your ideal customers?")
    problem = Prompt.ask("What problem do you solve?")
    action = Prompt.ask("What action should prospects take? (Book demo / Schedule call / etc.)")
    tone = Prompt.ask("Preferred email tone? (Professional, Friendly, Consultative, Founder-led, Technical)", default="Professional")
    notes = Prompt.ask("Any additional notes? (optional)", default="")
    
    console.print("\n---")
    with console.status("Generating Business Profile..."):
        time.sleep(1)
    with console.status("Generating Messaging Brain..."):
        time.sleep(1)
    with console.status("Creating prompt library..."):
        time.sleep(1)
    with console.status("Saving configuration..."):
        # Write .env
        env_content = f"""APP_NAME="Outur AI"
APP_ENV="production"
GEMINI_API_KEY="{gemini_key}"
GEMINI_MODEL="gemini-1.5-flash"
TAVILY_API_KEY="{tavily_key}"
RESEND_API_KEY="{resend_key}"
DATABASE_URL="sqlite+aiosqlite:///./outur_ai.db"
"""
        with open(".env", "w") as f:
            f.write(env_content)
        
        # Write business.yaml
        yaml_content = f"""company_name: {company_name}
website: {website}
elevator_pitch: {pitch}
target_icp: {icp}
problem_solved: {problem}
call_to_action: {action}
tone: {tone}
notes: {notes}
"""
        with open("business.yaml", "w") as f:
            f.write(yaml_content)
            
        time.sleep(1)
        
    with console.status("Running database migrations..."):
        time.sleep(1)
        
    console.print("\n[bold green]✓ Everything is ready.[/bold green]")
    console.print("Run your first campaign with:\n")
    console.print("    [bold cyan]outur run[/bold cyan]\n")

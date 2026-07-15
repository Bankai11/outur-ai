import typer
from rich.console import Console
from rich.prompt import Confirm
import time

console = Console()

def run_send():
    """
    Send all approved email drafts.
    """
    console.print("\n[bold blue]🚀 Send Approved Emails[/bold blue]\n")
    
    # Mocking sending
    approved_count = 15
    console.print(f"You have [bold green]{approved_count}[/bold green] approved emails ready to send.")
    
    if not Confirm.ask("Send them now?"):
        console.print("Cancelled.")
        return
        
    with console.status("Sending emails..."):
        time.sleep(2)
        
    console.print(f"[bold green]✓ Successfully sent {approved_count} emails![/bold green]\n")

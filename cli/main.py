import typer
from rich.console import Console

from cli.commands import init, run, doctor, config, review, send

app = typer.Typer(
    name="outur",
    help="Outur AI - AI Business Development Platform",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
console = Console()

# Register commands
app.command(name="init", help="Initial setup wizard to configure Outur AI.")(init.run_init)
app.command(name="run", help="Launch a new campaign using natural language.")(run.run_campaign)
app.command(name="doctor", help="Check system health and API connections.")(doctor.run_doctor)
app.command(name="config", help="View or update current configuration.")(config.run_config)
app.command(name="review", help="Review drafted emails pending approval.")(review.run_review)
app.command(name="send", help="Send all approved email drafts.")(send.run_send)

@app.callback()
def main_callback():
    """
    Outur AI - AI Sales Platform
    """
    pass

if __name__ == "__main__":
    app()

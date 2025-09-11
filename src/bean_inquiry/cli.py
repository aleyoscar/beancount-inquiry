import typer
from .bean_inquiry import bean_inquiry

app = typer.Typer()
app.command()(bean_inquiry)

if __name__ == "__main__":
    app()

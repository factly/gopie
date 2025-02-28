from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.json import JSON

class CliUI:
    def __init__(self):
        self.console = Console()

    def get_user_input(self, prompt: str = "\n[bold green]You[/bold green] > ") -> str:
        """Get user input from the console with an optional custom prompt

        Args:
            prompt: The prompt to display to the user. Defaults to a styled prompt

        Returns:
            The user's input as a string
        """
        try:
            self.console.print(
                "[dim]Type 'exit', 'quit' or 'q' to end the conversation[/dim]",
                style="italic",
            )
            return self.console.input(prompt)
        except (KeyboardInterrupt, EOFError):
            return "exit"

    def display_assistant_message(self, message: str) -> None:
        """Display assistant's message in a nice format"""
        self.console.print(
            Panel(
                Markdown(message),
                title="[bold purple]Assistant[/bold purple]",
                border_style="purple",
                padding=(1, 2),
            )
        )

    def display_exit(self) -> None:
        """Display exit message"""
        self.console.print(
            Panel("[bold]👋 Goodbye![/bold]", border_style="purple", padding=(1, 2))
        )

    def display_intermediate_step(self, content: str):
        """Display intermediate processing steps in a distinct format"""
        try:
            json_content = JSON.from_data(content) if isinstance(content, dict) else content
            self.console.print(
                Panel(
                    json_content,
                    title="[blue]🔄 Processing Step[/blue]",
                    border_style="blue",
                    padding=(1, 1)
                )
            )
        except Exception:
            self.console.print(f"🔄 [blue italic]Processing step:[/] {content}", soft_wrap=True)

    def display_error_message(self, message: str):
        """Display error message in a distinct format"""
        self.console.print(
            Panel(
                message,
                title="[red]❌ Error[/red]",
                border_style="red",
                padding=(1, 1)
            )
        )

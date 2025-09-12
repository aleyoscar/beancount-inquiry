import typer
import sys
import ast
import json
import re
from pathlib import Path
from typing import Optional, Union, Dict, List, Set
from typing_extensions import Annotated
from beancount import loader
from beancount.core.data import Query
from beanquery import query
from beanquery.query_render import render_text, render_csv

def load_ledger(ledger_path: Path) -> Optional[tuple[list, dict]]:
    """Load a Beancount ledger file and handle potential errors."""
    if not ledger_path.is_file():
        typer.echo(f"Error: '{ledger_path}' is not a valid file")
        return None
    try:
        entries, errors, options = loader.load_file(ledger_path)
        if errors:
            typer.echo(f"Warning: Found {len(errors)} errors while loading ledger:")
            for error in errors:
                typer.echo(f"  - {str(error)}")
        return entries, options
    except Exception as e:
        typer.echo(f"Error parsing Beancount file: {str(e)}")
        return None

def run_query(entries: list, options: dict, query_string: str) -> Optional[tuple[list, list]]:
    """Execute a Beancount query and handle potential errors."""
    try:
        rtypes, rrows = query.run_query(entries, options, query_string, numberify=True)
        return rtypes, rrows
    except Exception as e:
        typer.echo(f"Error executing query: {str(e)}")
        return None, None

def parse_params(params: str) -> Union[str, List, Dict, None]:
    """Safely parse parameter string into appropriate Python type."""
    if not params:
        return ""
    try:
        # First try JSON parsing for more robust handling
        return json.loads(params)
    except json.JSONDecodeError:
        try:
            # Fall back to ast.literal_eval for Python literals
            return ast.literal_eval(params)
        except (ValueError, SyntaxError) as e:
            typer.echo(f"Error parsing parameters: {str(e)}")
            return None

def validate_format(format_type: str) -> bool:
    """Validate the output format."""
    valid_formats = {"text", "csv"}
    if format_type not in valid_formats:
        typer.echo(f"Error: Invalid format '{format_type}'. Supported formats: {', '.join(valid_formats)}")
        return False
    return True

def extract_required_params(query_string: str) -> Set[str]:
    """Extract parameter placeholders from a query string."""
    # Find all placeholders like {0}, {1}, {name}, or {}
    placeholders = set()

    # Match named and indexed placeholders (e.g., {name}, {0}, {1})
    named_or_indexed = re.findall(r'\{([^}]*)\}', query_string)
    for placeholder in named_or_indexed:
        if placeholder:  # Non-empty, so it's named or indexed
            placeholders.add(placeholder)

    # Check for unnamed placeholders (e.g., {})
    # Count occurrences of {} by replacing named/indexed ones temporarily
    temp_string = re.sub(r'\{[^}]+\}', '', query_string)
    unnamed_count = temp_string.count('{}')
    for i in range(unnamed_count):
        placeholders.add(str(i))  # Treat unnamed as indexed (0, 1, 2, ...)

    return placeholders

def bean_inquiry(
    ledger: Annotated[Path, typer.Argument(
        help="The Beancount ledger file to parse",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True)],
    name: Annotated[str, typer.Argument(help="The name of the query to parse")],
    params: Annotated[str, typer.Option(
        "--params", "-p",
        help="Parameters in JSON or Python literal format (e.g., '\"value\"', '[1,2]', '{\"key\": \"value\"}')",
        show_default=False)] = "",
    format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: 'text' or 'csv'",
        case_sensitive=False)] = "text",
    check: Annotated[bool, typer.Option(
        "--check", "-c",
        help="Check a query for what parameters are needed",
        show_default=False)] = False
) -> None:
    """
    Beancount Inquiry - A tool to inject parameters into Beancount queries.
    """
    # Validate output format
    if not validate_format(format):
        raise typer.Exit(code=1)

    # Load ledger
    result = load_ledger(ledger)
    if result is None:
        raise typer.Exit(code=1)
    entries, options = result

    # Find query by name
    query_entry = next((q for q in entries if isinstance(q, Query) and q.name == name), None)
    if not query_entry:
        typer.echo(f"Error: No query found with name '{name}' in ledger")
        raise typer.Exit(code=1)

    query_string = query_entry.query_string

    # Extract and display required parameters
    required_params = ["{" + s + "}" for s in extract_required_params(query_string)]
    if check:
        if required_params:
            typer.echo(f"Required parameters for query '{name}': {', '.join(sorted(required_params))}")
            raise typer.Exit()
        else:
            typer.echo(f"No parameters required for query '{name}'")
            raise typer.Exit()

    # Parse parameters
    parsed_params = parse_params(params)
    if parsed_params is None:
        raise typer.Exit(code=1)

    # Validate parameters against required ones
    if required_params:
        if not parsed_params:
            typer.echo("Error: Query requires parameters, but none were provided")
            raise typer.Exit(code=1)
        if isinstance(parsed_params, dict):
            missing_params = required_params - set(parsed_params.keys())
            if missing_params:
                typer.echo(f"Error: Missing required parameters: {', '.join(sorted(missing_params))}")
                raise typer.Exit(code=1)
        elif isinstance(parsed_params, (list, tuple)):
            if len(parsed_params) < len(required_params):
                typer.echo(f"Error: Expected {len(required_params)} parameters, but got {len(parsed_params)}")
                raise typer.Exit(code=1)
        elif isinstance(parsed_params, str) and len(required_params) > 1:
            typer.echo(f"Error: Single string parameter provided, but multiple parameters required: {', '.join(sorted(required_params))}")
            raise typer.Exit(code=1)

    # Format query with parameters
    try:
        if parsed_params:
            if isinstance(parsed_params, str):
                query_string = query_string.format(parsed_params)
            elif isinstance(parsed_params, (list, tuple)):
                query_string = query_string.format(*parsed_params)
            elif isinstance(parsed_params, dict):
                query_string = query_string.format(**parsed_params)
    except (KeyError, IndexError, ValueError) as e:
        typer.echo(f"Error formatting query with parameters: {str(e)}")
        raise typer.Exit(code=1)

    typer.echo(f"\nRunning query: {query_string}\n")

    # Execute query
    rtypes, rrows = run_query(entries, options, query_string)
    if rtypes is None or rrows is None:
        raise typer.Exit(code=1)

    # Render results
    try:
        if format == "text":
            render_text(rtypes, rrows, options['dcontext'], sys.stdout)
        elif format == "csv":
            render_csv(rtypes, rrows, options['dcontext'], sys.stdout)
    except Exception as e:
        typer.echo(f"Error rendering output: {str(e)}")
        raise typer.Exit(code=1)

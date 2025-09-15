import typer
import sys
import re
from pathlib import Path
from typing import Optional, Union, Dict, List, Set
from typing_extensions import Annotated
from enum import Enum
from beancount import loader
from beancount.core.data import Query
from beanquery import query
from beanquery.query_render import render_text, render_csv
from . import __version__

class Format(str, Enum):
    text = "text"
    csv = "csv"

class Placeholder(str, Enum):
    named = "named"
    indexed = "indexed"
    blank = "blank"

def which_type(text: str) -> Optional[str]:
    """Returns the type of the parameter"""
    if valid_pyname(text):
        return Placeholder.named
    elif valid_int(text):
        return Placeholder.indexed
    elif not text:
        return Placeholder.blank
    else:
        return None

def valid_pyname(name: str) -> bool:
    """Validates if a string is a valid python variable name"""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))

def valid_int(num: str) -> bool:
    """Validates if a string is a valid integer"""
    return bool(re.match(r'^\d+$', num))

def load_ledger(ledger_path: Path) -> Optional[tuple[list, dict]]:
    """Load a Beancount ledger file and handle potential errors."""
    if not ledger_path or not ledger_path.is_file():
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

def get_placeholders(query_string: str) -> Optional[tuple[Set[str], str]]:
    """Extract parameter placeholders from a query string."""
    # Find all placeholders like {0}, {1}, {name}, or {}
    placeholders = set()

    # Match all placeholders (e.g., {name}, {0}, {})
    matches = re.findall(r'\{([^}]*)\}', query_string)
    if not len(matches):
        return placeholders, ''
    expected = which_type(matches[0])
    if expected is not None:
        for placeholder in matches:
            if which_type(placeholder) != expected:
                return None
            else:
                placeholders.add(placeholder)
    else:
        return None

    return placeholders, expected

def parse_params(params: List[str], placeholders: Set[str], placeholders_type: str, placeholders_string: str) -> Optional[Union[List, Dict]]:
    """Parse parameters and return either a list or dict"""
    if not params and not placeholders:
        return []
    if (not params and placeholders) or (len(params) != len(placeholders)):
        typer.echo(f"Error: Parameter and placeholder count do not match, needed ({len(placeholders)}): {placeholders_string}")
        return None

    if placeholders_type == Placeholder.named:
        params_dict = {}
        for p in params:
            item = p.split(":", 1)
            if len(item) != 2:
                typer.echo(f"Error: Named parameters must each be split with a ':'")
                return None
            if item[0] not in placeholders:
                typer.echo(f"Error: Parameter key '{item[0]}' does not exist in placeholders: {placeholders_string}")
                return None
            params_dict[item[0]] = item[1]
        if not all(key in params_dict for key in placeholders):
            typer.echo(f"Error: Must provide all placeholder keys: {placeholders_string}")
            return None
        return params_dict

    return params

def run_query(entries: list, options: dict, query_string: str) -> Optional[tuple[list, list]]:
    """Execute a Beancount query and handle potential errors."""
    try:
        rtypes, rrows = query.run_query(entries, options, query_string, numberify=True)
        return rtypes, rrows
    except Exception as e:
        typer.echo(f"Error executing query: {str(e)}")
        return None, None

def bean_inquiry(
    ledger: Annotated[Path, typer.Argument(
        help="The Beancount ledger file to parse",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True
    )] = None,
    name: Annotated[str, typer.Argument(
        help="The name of the query to parse",
        show_default=False
    )] = "",
    params: Annotated[List[str], typer.Argument(
        help="List of parameters to parse",
        show_default=False
    )] = None,
    format: Annotated[Format, typer.Option(
        "--format", "-f",
        help="Output format: 'text' or 'csv'",
        case_sensitive=False
    )] = Format.text,
    check: Annotated[bool, typer.Option(
        "--check", "-c",
        help="Check a query for what parameters are needed",
        show_default=False
    )] = False,
    list_queries: Annotated[bool, typer.Option(
        "--list", "-l",
        help="List all queries available in ledger",
        show_default=False
    )] = False,
    version: Annotated[bool, typer.Option(
        "--version", "-v",
        help="Print version info",
        show_default=False
    )] = False
) -> None:
    """
    Beancount INquiry - A CLI tool to inject parameters INto Beancount queries located in your ledger.
    """

    # Print version info
    if version:
        typer.echo(f"Version: {__version__}")
        exit()

    # Load ledger
    if ledger is None:
        typer.echo(f"Error: Please provide a ledger file to parse")
        raise typer.Exit(code=1)
    result = load_ledger(ledger)
    if result is None:
        raise typer.Exit(code=1)
    entries, options = result

    # Find queries
    query_entries = [q for q in entries if isinstance(q, Query)]
    if not query_entries:
        typer.echo("Error: No queries found in ledger")
        raise typer.Exit(code=1)
    if list_queries:
        for q in query_entries:
            typer.echo(f"{q.name}")
        raise typer.Exit()

    # Get query string
    if not name:
        typer.echo("Error: You must supply a query name to parse")
        raise typer.Exit(code=1)
    query_entry = next((q for q in entries if isinstance(q, Query) and q.name == name), None)
    if not query_entry:
        typer.echo(f"Error: No query found with name '{name}' in ledger")
        raise typer.Exit(code=1)
    query_string = query_entry.query_string

    # Extract and display placeholders
    placeholders_result = get_placeholders(query_string)
    if not placeholders_result:
        typer.echo("Error: Invalid placeholder format. All placeholders must be of the same type. (e.g. named: {name}, indexed: {0}, or empty: {})")
        raise typer.Exit(code=1)
    placeholders, placeholders_type = placeholders_result
    placeholders_list = ["{" + p + "}" for p in placeholders]
    placeholders_string = ', '.join(sorted(placeholders_list))
    if check:
        if placeholders_list:
            typer.echo(f"Required parameters for query '{name}' ({len(placeholders)}): {placeholders_string}")
        else:
            typer.echo(f"No parameters required for query '{name}'")
        raise typer.Exit()

    # Parse parameters
    parsed_params = parse_params(params, placeholders, placeholders_type, placeholders_string)
    if parsed_params is None:
        raise typer.Exit(code=1)

    # Format query with parameters
    try:
        if parsed_params:
            if isinstance(parsed_params, (list, tuple)):
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
        if format == Format.text:
            render_text(rtypes, rrows, options['dcontext'], sys.stdout)
        elif format == Format.csv:
            render_csv(rtypes, rrows, options['dcontext'], sys.stdout)
    except Exception as e:
        typer.echo(f"Error rendering output: {str(e)}")
        raise typer.Exit(code=1)

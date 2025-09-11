import typer, sys, ast
from . import __version__
from beancount import loader
from beancount.core.data import Query
from beanquery import query
from beanquery.query_render import render_text, render_csv
from typing_extensions import Annotated
from pathlib import Path

def load_ledger(path):
    try:
        entries, errors, options = loader.load_file(path)
        return entries, options
    except FileNotFoundError:
        print(f"Error: File {path} not found")
        return None
    except Exception as e:
        print(f"Error parsing Beancount file: {str(e)}")
        return None

def run_query(entries, options, inquiry):
    try:
        rtypes, rrows = query.run_query(entries, options, inquiry, numberify=True)
        return rtypes, rrows
    except Exception as e:
        print(f"Error running query: {str(e)}")
        return None, None

def bean_inquiry(
    ledger: Annotated[Path, typer.Argument(help="The beancount ledger file to parse", exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True)],
    name: Annotated[str, typer.Argument(help="The name of the query to parse")],
    params: Annotated[str, typer.Option("--params", "-p", help="Parameters string in JSON format", callback=ast.literal_eval)]="",
    format: Annotated[str, typer.Option("--format", "-f", help="Format to print output as. Can be either 'csv' or 'text'")]="text"
):
    """
    Beancount Inquiry - A bean-query tool to insert parameters into your queries
    """

    # Load ledger
    entries, options = load_ledger(ledger)

    # Get query directives
    queries = [q for q in entries if isinstance(q, Query)]

    # Select query
    if len(queries):
        inquiry = None
        for i in queries:
            if i.name == name:
                inquiry = i.query_string
        if inquiry is None:
            print(f"No query found with the name {name}")
        else:

            # Parse parameters and insert into query
            if params != '':
                if isinstance(params, str):
                    inquiry = inquiry.format(params)
                if isinstance(params, list):
                    inquiry = inquiry.format(*params)
                if isinstance(params, dict):
                    inquiry = inquiry.format(**params)
            print(f"\nRunning query: {inquiry}\n")

            # Get query results
            rtypes, rrows = run_query(entries, options, inquiry)

            # Render results
            if format == 'text':
                render_text(rtypes, rrows, options['dcontext'], sys.stdout)
            elif format == 'csv':
                render_csv(rtypes, rrows, options['dcontext'], sys.stdout)
            else:
                print(f"Invalid format type {format}")
    else:
        print(f"No quieries found in ledger")

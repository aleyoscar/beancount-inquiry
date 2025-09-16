# import typer
import sys
import re
import argparse
import subprocess
import shutil
from io import TextIOWrapper
from pathlib import Path
from typing import Optional, Union, Dict, List, Set
from enum import Enum

__version__ = '0.2.1'

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

def valid_query(line: str) -> Optional[dict]:
    """Validates if a string is a query directive and returns a dictionary with the separate parts"""
    pattern = r'^\s*(\d{4}-\d{2}-\d{2})\s+query\s+"([^"]+)"\s+"([^"]*)"\s*$'
    match = re.match(pattern, line.strip())
    if match:
        return {
            'date': match.group(1),
            'name': match.group(2),
            'query_string': match.group(3)
        }
    return None

def load_queries(ledger_file: TextIOWrapper) -> Optional[list]:
    """Load a Beancount ledger file and extract the query directives"""
    query_entries = []
    for line in ledger_file:
        query = valid_query(line)
        if query:
            query_entries.append(query)
    return query_entries if len(query_entries) else None

def get_placeholders(query_string: str) -> Optional[tuple[List[str], str]]:
    """Extract parameter placeholders from a query string."""
    # Find all placeholders like {0}, {1}, {name}, or {}
    placeholders = []

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
                placeholders.append(placeholder)
    else:
        return None

    if expected != Placeholder.blank:
        placeholders = list(set(placeholders))

    return placeholders, expected

def parse_params(params: List[str], placeholders: List[str], placeholders_type: str, placeholders_string: str) -> Optional[Union[List, Dict]]:
    """Parse parameters and return either a list or dict"""
    if not params and not placeholders:
        return []
    if (not params and placeholders) or (len(params) != len(placeholders)):
        print(f"Error: Parameter and placeholder count do not match, needed ({len(placeholders)}): {placeholders_string}")
        return None

    if placeholders_type == Placeholder.named:
        params_dict = {}
        for p in params:
            item = p.split(":", 1)
            if len(item) != 2:
                print(f"Error: Named parameters must each be split with a ':'")
                return None
            if item[0] not in placeholders:
                print(f"Error: Parameter key '{item[0]}' does not exist in placeholders: {placeholders_string}")
                return None
            params_dict[item[0]] = item[1]
        if not all(key in params_dict for key in placeholders):
            print(f"Error: Must provide all placeholder keys: {placeholders_string}")
            return None
        return params_dict

    return params

def main():
    parser = argparse.ArgumentParser(
        prog='Beancount INquiry',
        description='Beancount INquiry - A CLI tool to inject parameters INto Beancount queries located in your ledger.'
    )
    parser.add_argument('ledger', help="The Beancount ledger file to parse", nargs="?", type=argparse.FileType('r', encoding='utf-8'))
    parser.add_argument('name', help="The name of the query to parse", nargs="?")
    parser.add_argument('params', help="List of parameters to parse", nargs="*")
    parser.add_argument('-f', '--format', help="Output format: 'text' or 'csv'", choices=['text', 'csv'], default='text')
    parser.add_argument('-c', '--check', action='store_true', help="Check a query for what parameters are needed")
    parser.add_argument('-l', '--list', action='store_true', help="List all queries available in ledger")
    parser.add_argument('-v', '--version', action='version', help="Print version info", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    print(f"ledger: {args.ledger} ({type(args.ledger)})")
    print(f"name: {args.name} ({type(args.name)})")
    print(f"params: {args.params} ({type(args.params)})")
    print(f"format: {args.format} ({type(args.format)})")
    print(f"check: {args.check} ({type(args.check)})")
    print(f"list: {args.list} ({type(args.list)})")

    # Load ledger
    if args.ledger is None:
        sys.exit(f"Error: Please provide a ledger file to parse")
    query_entries = load_queries(args.ledger)
    if query_entries is None:
        sys.exit(f"Error: No queries found in ledger")
    if args.list:
        for q in query_entries:
            print(f"{q['name']}")
        sys.exit()

    # # Get query string
    if not args.name:
        sys.exit("Error: You must supply a query name to parse")
    query_entry = next((q for q in query_entries if q['name'] == args.name), None)
    if not query_entry:
        sys.exit(f"Error: No query found with name '{args.name}' in ledger. Valid queries: {', '.join([q['name'] for q in query_entries])}")
    query_string = query_entry['query_string']
    print(f"QUERY   : {query_string}")

    # Extract and display placeholders
    placeholders_result = get_placeholders(query_string)
    if not placeholders_result:
        sys.exit("Error: Invalid placeholder format. All placeholders must be of the same type. (e.g. named: {name}, indexed: {0}, or empty: {})")
    placeholders, placeholders_type = placeholders_result
    placeholders_list = ["{" + p + "}" for p in placeholders]
    placeholders_string = ', '.join(sorted(placeholders_list))
    if args.check:
        if placeholders_list:
            print(f"Required parameters for query '{args.name}' ({len(placeholders)}): {placeholders_string}")
        else:
            print(f"No parameters required for query '{args.name}'")
        sys.exit()

    # Parse parameters
    parsed_params = parse_params(args.params, placeholders, placeholders_type, placeholders_string)
    if parsed_params is None:
        sys.exit(1)

    # Format query with parameters
    try:
        if parsed_params:
            if isinstance(parsed_params, (list, tuple)):
                query_string = query_string.format(*parsed_params)
            elif isinstance(parsed_params, dict):
                query_string = query_string.format(**parsed_params)
            print(f"INJECTED: {query_string}")
    except (KeyError, IndexError, ValueError) as e:
        sys.exit(f"Error formatting query with parameters: {str(e)}")

    # Execute query
    if not shutil.which('bean-query'):
        sys.exit(f"Error: bean-query is not installed on the system")
    try:
        print()
        query_result = subprocess.run(
            ["bean-query", "-f", args.format, args.ledger.name, query_string],
            check=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error running query {str(e)}")

if __name__ == "__main__":
    main()

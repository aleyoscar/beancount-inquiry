# Beancount INquiry

A CLI tool to INject parameters into Beancount queries specified in your ledger

## Usage

Beancount INquiry will inject parameters into query directives specified in your ledger file using pythons `.format` function, and so uses the same syntax. Here is an example query directive with two parameters located in `ledger.beancount`:

```
2025-01-01 query "balance" "SELECT date, account, sum(number) as total WHERE account ~ '{}' AND date >= {} ORDER BY account"
```

Parameters must be specified using either a JSON string or Python literal, must be enclosed in quotes and can be either a string, list or dictionary. For example for the query above the parameters could be written as:

```
'["Assets:Bank", "2025-05-01"]' # JSON string
"['Assets:Bank', '2025-05-01']" # Python literal
```

> Note: You may need to escape double quotes depending on your shell, e.g.: '[\"Assets:Bank\", \"2025-05-01\"]'

And so the entire command would be:

```
bean-inquiry ledger.beancount balance '["Assets:Bank", "2025-05-01"]' # JSON string
bean-inquiry ledger.beancount balance "['Assets:Bank', '2025-05-01']" # Python literal
```

You can also specify indexed parameters:

```
2025-01-01 query "balance" "SELECT date, {0}, sum(number) as total WHERE {0} ~ '{1}' AND date >= {2} ORDER BY {0}"
...
bean-inquiry ledger.beancount balance "['account', 'Assets:Bank', '2025-05-01']" # Python literal
```

And named parameters:

```
2025-01-01 query "balance" "SELECT date, account, sum(number) as total WHERE account ~ '{account}' AND date >= {date} ORDER BY account"
...
bean-inquiry ledger.beancount balance "{'account':'Assets:Bank', 'date':'2025-05-01'}" # Python literal
```

> Note: Named parameters must be a dictionary, hence the `{}`

For queries with only a single parameter, a string can be used:

```
2025-01-01 query "balance" "SELECT date, account, sum(number) as total WHERE account ~ '{}' ORDER BY account"
...
bean-inquiry ledger.beancount balance "'Assets:ANB'" # Python literal
```

> Note: Since you must pass in a Python literal string, you must enclose the value in quotes.

Since JSON does not support a single string value, if passing in a JSON string you must supply an array with a single value

```
bean-inquiry ledger.beancount balance '["Assets:ANB"]' # JSON string
```

## Options

Usage: bean-inquiry [OPTIONS] LEDGER [NAME] [PARAMS]

╭─ Arguments ───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    ledger      FILE      The Beancount ledger file to parse [required]                                          │
│      name        [NAME]    The name of the query to parse                                                         │
│      params      [PARAMS]  Parameters in JSON or Python literal format (e.g., '"value"', '[1,2]', '{"key":        │
│                            "value"}')                                                                             │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --format              -f      TEXT  Output format: 'text' or 'csv' [default: text]                                │
│ --check               -c            Check a query for what parameters are needed                                  │
│ --list                -l            List all queries available in ledger                                          │
│ --help                              Show this message and exit.                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

## Installation

### Pipx (recommended)

Install using pipx from [PyPi](https://pypi.org)

```
pipx install beancount-inquiry
bean-inquiry --help
```

### Build from source

Clone this repository and install systemwide using pipx:

```
git clone https://github.com/aleyoscar/beancount-inquiry.git
cd beancount-inquiry
pipx install .
bean-inquiry --help
```

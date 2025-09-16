# Beancount INquiry

A CLI tool to INject parameters into Beancount queries specified in your ledger

## Usage

Beancount INquiry will inject parameters into query directives specified in your ledger file using pythons `.format` function, and so uses the same syntax. Here is an example query directive with two parameters:

```
2025-01-01 query "balance" "SELECT date, account, sum(number) as total WHERE account ~ '{}' AND date >= {} ORDER BY account"
```

And then pass in the ledger, the name of the query, and the list of parameters

```
bean-inquiry ledger.beancount balance Assets 2014-05-01
```

You can also use indexed placeholders:

```
2025-01-01 query "balance" "SELECT date, {0}, sum(number) as total WHERE {0} ~ '{1}' AND date >= {2} ORDER BY {0}"
...
bean-inquiry ledger.beancount balance account Assets:Bank 2025-05-01
```

And named placeholders, with parameter keys separated with a colon:

```
2025-01-01 query "balance" "SELECT date, {select}, sum(number) as total WHERE {select} ~ '{account}' AND date >= {date} ORDER BY {select}"
...
bean-inquiry ledger.beancount balance select:account account:Assets:Bank date:2025-05-01
```

See the `--help` for more options

```
bean-inquiry --help
```

## Installation

There are two different versions of Beancunt INquiry, the **[CLI tool](#cli)** and the **[script](#script)**, the main difference being that the **CLI tool** can run stand-alone and has `beanquery` as a dependency, and the **script** does not have dependencies but needs `bean-query` installed on your system and in your PATH. Also currently the **script** can only run query directives that are on a single line in your ledger, whereas the **CLI tool** can run query directives that traverse multiple lines.

### CLI

#### Pipx (recommended)

Install using pipx from [PyPi](https://pypi.org)

```
pipx install bean-inquiry
bean-inquiry --help
```

#### Build from source using pipx

Clone this repository and install systemwide using pipx:

```
git clone https://github.com/aleyoscar/beancount-inquiry.git
cd beancount-inquiry
pipx install .
bean-inquiry --help
```

#### Run using poetry

Clone this repository and run using [poetry](https://python-poetry.org/)

```
git clone https://github.com/aleyoscar/beancount-inquiry.git
cd beancount-inquiry
poetry install
poetry run bean-inquiry
```

### Script

Does not need `beanquery`, but does need the `bean-query` executable installed on your system and in your PATH. Simply download [bean-inquiry.py](https://github.com/aleyoscar/beancount-inquiry/blob/main/bean-inquiry.py) or clone this repository and run the script `bean-inquiry.py` in the root project folder:

```
python bean-inquiry.py --help
```

## Dependencies

This project uses [beancount](https://github.com/beancount/beancount) to parse the ledger and [beanquery](https://github.com/beancount/beanquery) for running the queries.

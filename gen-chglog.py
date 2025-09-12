import os, re, subprocess, shutil, typer
from typing_extensions import Annotated
from rich.console import Console
from rich.theme import Theme
from typing import List
from pathlib import Path

theme = Theme({"number": "cyan", "error": "red", "file": "grey50", "warning": "yellow", "success": "green"})
console = Console(theme=theme, highlighter=None)
semver_pattern = r"^v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>alpha|beta|rc)(?:\.(?P<version>0|[1-9]\d*))?)?$"

def installed(process):
	if shutil.which(process):
		console.print(f"[success]{process} is installed.[/]")
		return True
	else:
		console.print(f"[error]{process} is not installed[/]")
		return False

def run(command, message=''):
	try:
		result = subprocess.run(
			command,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			check=True,
			text=True
		)
		if message:
			console.print(message)
		else:
			console.print(f"{' '.join(command)} ... [success]DONE[/]")
		return result.stdout.strip()
	except subprocess.CalledProcessError as e:
		error_quit(f"{' '.join(command)} ... [error]ERROR: {e}[/]")
		return None

def update_version(file_path, old_version, new_version):
	with open(file_path, 'r', encoding='utf-8') as file:
		content = file.read()
	updated_content = content.replace(old_version[1:], new_version[1:])

	with open(file_path, 'w', encoding='utf-8', newline='\n') as file:
		file.write(updated_content)

	console.print(f"[success]Updated version info: [/][file]{file_path}[/]")

def error_quit(message):
	console.print(f"[error]<<ERROR>> {message}[/]")
	exit()

def version_callback(ver_str: str):
	if not re.fullmatch(semver_pattern, ver_str):
		raise typer.BadParameter("Please enter a valid semantic version pattern (e.g., v1.0.1)")
	return ver_str

def main(
	version: Annotated[str, typer.Argument(
		help="New version string (e.g., v1.0.1)",
		callback=version_callback)],
	replace: Annotated[List[Path], typer.Option(
		"--replace", "-r",
		help="A file to search and replace previous version with new version",
		exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True)]=[],
	dry: Annotated[bool, typer.Option("--dry", "-d", help="Dry run, do not commit")]=False,
	output: Annotated[Path, typer.Option("--output", "-o", help="Specify output changelog file, default is 'CHANGELOG.md'",
		exists=False)]="./CHANGELOG.md",
	config: Annotated[Path, typer.Option("--config", "-c", help="Specify the config file path, default is '.chglog/config-tag.yml'",
		exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True)]=".chglog/config-tag.yml",
	temp: Annotated[Path, typer.Option("--temp", "-t", help="Specify the temp file path, default is '.chglog/current-tag.md'",
		exists=False)]=".chglog/current-tag.md"
):
	"""
	Create CHANGELOG using git-chglog and update version info

	Optionally specify a file to --replace the previous version string with the new version
	Optionally specify a --dry run without commiting or writing to files
	Optionally specify the --output CHANGELOG path. Default is 'CHANGELOG.md'
	Optionally specify the git-chglog --config path. Default is '.chglog/config-tag.yml'
	Optionally specify the --temp file path. Default is '.chglog/current-tag.md'
	"""
	if not installed('git'):
		error_quit(f"Please install git")
	if not installed('git-chglog'):
		error_quit(f"Please install git-chglog")
	if len(replace):
		prev_version = run(['git', 'describe', '--tags', '--abbrev=0'], "[success]Getting previous version[/]")
		if not re.fullmatch(semver_pattern, prev_version):
			error_quit(f"Invalid previous version [number]{prev_version}[/]")
		else:
			console.print(f"Previous version: [number]{prev_version}[/]")
		for path in replace:
			if not dry: update_version(path, prev_version, version)
			else: console.print(f"[success]Will update version info in [file]{path}[/][/]")
	if dry:
		run(['git-chglog', '--next-tag', version])
		run(['git-chglog', '--config', str(config), '--next-tag', version, version])
	else:
		run(['git-chglog', '--next-tag', version, '-o', str(output)], f"[success]Writing changelog to [file]{output}[/][/]")
		run(['git-chglog', '--config', str(config), '--next-tag', version, '-o', str(temp), version], f"[success]Writing tag annotation to [file]{temp}[/][/]")
		run(['git', 'commit', '-am', f"release {version}"], f"[success]Commiting release[/]")
		run(['git', 'tag', version, '-F', str(temp)], f"[success]Creating git tag [number]{version}[/][/]")
	console.print(f"[success]DONE[/]")
	if not dry: console.print(f"[warning]Remember to run [file]'git push && git push origin --tags'[/][/]")

if __name__ == '__main__':
	typer.run(main)

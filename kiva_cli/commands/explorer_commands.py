#!/usr/bin/env python3
"""
Windows Explorer Skill - KIVA CLI

Provides integration with Windows Explorer for file navigation and path management.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click


def _open_explorer(path: str):
    """Open Windows Explorer at the specified path."""
    if sys.platform != "win32":
        click.echo(click.style("Windows Explorer is only available on Windows.", fg="red"))
        return False
    
    path_obj = Path(path)
    if not path_obj.exists():
        click.echo(click.style(f"Path does not exist: {path}", fg="red"))
        return False
    
    try:
        if path_obj.is_file():
            # Select file in Explorer - use start command
            os.startfile(str(path_obj))
        else:
            # Open folder in Explorer
            os.startfile(str(path_obj))
        return True
    except Exception as e:
        click.echo(click.style(f"Failed to open Explorer: {e}", fg="red"))
        return False
    
    path_obj = Path(path)
    if not path_obj.exists():
        click.echo(click.style(f"Path does not exist: {path}", fg="red"))
        return False
    
    try:
        if path_obj.is_file():
            # Select file in Explorer - use start command
            os.startfile(str(path_obj))
        else:
            # Open folder in Explorer
            os.startfile(str(path_obj))
        return True
    except Exception as e:
        click.echo(click.style(f"Failed to open Explorer: {e}", fg="red"))
        return False


def _copy_to_clipboard(text: str):
    """Copy text to Windows clipboard."""
    if sys.platform != "win32":
        click.echo(click.style("Clipboard operations are only available on Windows.", fg="red"))
        return False
    
    try:
        subprocess.run(["clip"], input=text.encode("utf-8"), check=True)
        return True
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f"Failed to copy to clipboard: {e}", fg="red"))
        return False


@click.group(name='explorer')
def explorer_cli():
    """
    Windows Explorer integration.

    Provides:
    - Open Explorer at a path
    - Select a file in Explorer
    - Copy paths to clipboard
    - Convert and copy paths (local/remote)
    """
    pass


@explorer_cli.command(name='open')
@click.argument('path', default='.')
def open_explorer(path: str):
    """
    Open Windows Explorer at the specified path.

    PATH: Path to open (default: current directory)

    Example:
        kiva explorer open C:\\DevTools\\bin
    """
    if _open_explorer(path):
        click.echo(click.style(f"Opened Explorer at: {path}", fg="green"))


@explorer_cli.command(name='select')
@click.argument('file_path')
def select_file(file_path: str):
    """
    Select a file in Windows Explorer.

    FILE_PATH: Path to the file to select

    Example:
        kiva explorer select C:\\DevTools\\bin\\script.ps1
    """
    if _open_explorer(file_path):
        click.echo(click.style(f"Selected file in Explorer: {file_path}", fg="green"))


@explorer_cli.command(name='copy-path')
@click.argument('path', default='.')
@click.option('--remote', '-r', is_flag=True, help='Copy remote path instead of local')
def copy_path(path: str, remote: bool):
    """
    Copy path to clipboard.

    PATH: Path to copy (default: current directory)

    Example:
        kiva explorer copy-path
        kiva explorer copy-path --remote
    """
    from kiva_cli.core.path_resolver import PathResolver
    
    resolver = PathResolver()
    resolved = resolver.resolve(path)
    
    if remote and resolved.get('remote'):
        path_to_copy = resolved['remote']
    else:
        path_to_copy = resolved.get('local', path)
    
    if _copy_to_clipboard(path_to_copy):
        click.echo(click.style(f"Copied to clipboard: {path_to_copy}", fg="green"))


@explorer_cli.command(name='convert')
@click.argument('path')
@click.option('--to', '-t', 'target_format', default='auto', type=click.Choice(['local', 'remote', 'auto']), help='Target format')
def convert_and_copy(path: str, target_format: str):
    """
    Convert path and copy to clipboard.

    PATH: Path to convert

    Example:
        kiva explorer convert C:\\DevTools\\bin\\script.ps1
        kiva explorer convert gerivdb/DevTools/bin/script.ps1 --to local
    """
    from kiva_cli.core.path_resolver import PathResolver
    
    resolver = PathResolver()
    converted = resolver.convert_path(path, target_format)
    
    if converted == path:
        click.echo(click.style(f"Could not convert: {path}", fg="yellow"))
        return
    
    if _copy_to_clipboard(converted):
        click.echo(click.style(f"Converted and copied: {converted}", fg="green"))
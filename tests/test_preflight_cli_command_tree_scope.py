from __future__ import annotations

import click
from typer.main import get_command

from app.preflight.interface.cli import cli_app


def _collect_group_paths(group: click.Group, parent: str = "") -> set[str]:
    paths: set[str] = set()
    for name, command in group.commands.items():
        path = f"{parent} {name}".strip()
        paths.add(path)
        if isinstance(command, click.Group):
            paths.update(_collect_group_paths(command, path))
    return paths


def test_preflight_cli_command_tree_stays_within_mvp_scope() -> None:
    root = get_command(cli_app)
    assert isinstance(root, click.Group)

    command_paths = _collect_group_paths(root)
    assert command_paths == {
        "topic",
        "topic dry-run",
        "topic apply",
        "schema",
        "schema dry-run",
        "schema apply",
    }

    forbidden_surfaces = ("connect", "monitoring", "dashboard")
    assert not any(
        any(surface in segment for surface in forbidden_surfaces)
        for path in command_paths
        for segment in path.split()
    )

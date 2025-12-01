"""Discover and parse Claude command files."""
import logging
import re
from pathlib import Path

import yaml

from .models import ClaudeCommand

logger = logging.getLogger(__name__)


def parse_command_file(path: Path, source: str = "personal") -> ClaudeCommand:
    """Parse a .md command file into a ClaudeCommand.

    Args:
        path: Path to the .md file.
        source: Where command came from ("personal" or "project").

    Returns:
        Parsed ClaudeCommand.
    """
    content = path.read_text()
    name = path.stem  # filename without extension

    # Parse frontmatter if present
    frontmatter = {}
    prompt = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                pass  # Invalid YAML, skip frontmatter
            prompt = parts[2].strip()

    # Get description from frontmatter or first line of prompt
    description = frontmatter.get("description", "")
    if not description:
        first_line = prompt.split("\n")[0].strip()
        description = first_line[:256] if first_line else name

    # Truncate description to Telegram limit
    if len(description) > 256:
        description = description[:253] + "..."

    # Check if command needs arguments
    needs_args = bool(
        re.search(r"\$ARGUMENTS|\$[1-9]", prompt)
    )

    return ClaudeCommand(
        name=name,
        description=description,
        prompt=prompt,
        needs_args=needs_args,
        source=source,
    )


def scan_commands(project_path: str | None = None) -> list[ClaudeCommand]:
    """Scan personal and project directories for commands.

    Personal commands from ~/.claude/commands/ are loaded first,
    then project commands override any with the same name.

    Args:
        project_path: Optional project directory path.

    Returns:
        List of discovered commands, with project commands taking priority.
    """
    commands: dict[str, ClaudeCommand] = {}

    # 1. Scan personal commands
    personal_dir = Path.home() / ".claude" / "commands"
    if personal_dir.is_dir():
        for md_file in personal_dir.glob("*.md"):
            try:
                cmd = parse_command_file(md_file, source="personal")
                commands[cmd.name] = cmd
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")

    # 2. Scan project commands (override personal)
    if project_path:
        project_dir = Path(project_path) / ".claude" / "commands"
        if project_dir.is_dir():
            for md_file in project_dir.glob("*.md"):
                try:
                    cmd = parse_command_file(md_file, source="project")
                    commands[cmd.name] = cmd
                except Exception as e:
                    logger.warning(f"Failed to parse {md_file}: {e}")

    return list(commands.values())

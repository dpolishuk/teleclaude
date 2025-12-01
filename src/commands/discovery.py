"""Discover and parse Claude command files."""
import re
from pathlib import Path

import yaml

from .models import ClaudeCommand


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

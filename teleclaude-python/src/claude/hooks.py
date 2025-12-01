"""Claude SDK hooks for approval workflow."""
from typing import Any

# Patterns that require user approval
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -r /",
    "sudo rm",
    "sudo",
    "git push --force",
    "git push -f",
    "chmod 777",
    "chmod -R 777",
    "> /dev/sd",
    "mkfs.",
    "dd if=",
    ":(){:|:&};:",  # Fork bomb
    "wget | sh",
    "curl | sh",
]


def is_dangerous_command(command: str) -> bool:
    """Check if command matches dangerous patterns."""
    command_lower = command.lower()
    return any(pattern in command_lower for pattern in DANGEROUS_PATTERNS)


async def check_dangerous_command(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """PreToolUse hook to intercept dangerous operations."""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")

    if is_dangerous_command(command):
        # Find which pattern matched
        matched = next(
            (p for p in DANGEROUS_PATTERNS if p in command.lower()),
            "dangerous pattern",
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"Command contains: {matched}",
            }
        }

    return {}


def create_approval_hooks(dangerous_commands: list[str] | None = None) -> dict:
    """Create hooks dict for ClaudeAgentOptions."""
    return {
        "PreToolUse": {
            "Bash": [check_dangerous_command],
        }
    }

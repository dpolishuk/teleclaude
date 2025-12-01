"""Claude SDK hooks for approval workflow."""
from typing import Any, Callable

from claude_agent_sdk import HookMatcher

# Default patterns that require user approval (must be lowercase)
DANGEROUS_PATTERNS: list[str] = [
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


def is_dangerous_command(
    command: str, patterns: list[str] | None = None
) -> bool:
    """Check if command matches dangerous patterns.

    Args:
        command: The command to check.
        patterns: Custom patterns to check against. If None, uses DANGEROUS_PATTERNS.

    Returns:
        True if command matches any dangerous pattern.
    """
    check_patterns = patterns if patterns is not None else DANGEROUS_PATTERNS
    command_lower = command.lower()
    return any(pattern.lower() in command_lower for pattern in check_patterns)


def _find_matched_pattern(
    command: str, patterns: list[str]
) -> str:
    """Find which pattern matched the command."""
    command_lower = command.lower()
    return next(
        (p for p in patterns if p.lower() in command_lower),
        "dangerous pattern",
    )


async def check_dangerous_command(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """PreToolUse hook to intercept dangerous operations.

    Uses the default DANGEROUS_PATTERNS list.
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")

    if is_dangerous_command(command):
        matched = _find_matched_pattern(command, DANGEROUS_PATTERNS)

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"Command contains: {matched}",
            }
        }

    return {}


def create_dangerous_command_hook(
    patterns: list[str],
) -> Callable[[dict[str, Any], str | None, dict[str, Any]], Any]:
    """Create a hook function with custom dangerous patterns.

    Args:
        patterns: List of patterns to check against.

    Returns:
        An async hook function for PreToolUse.
    """
    async def hook(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name != "Bash":
            return {}

        command = tool_input.get("command", "")

        if is_dangerous_command(command, patterns):
            matched = _find_matched_pattern(command, patterns)

            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": f"Command contains: {matched}",
                }
            }

        return {}

    return hook


def create_approval_hooks(dangerous_commands: list[str] | None = None) -> dict:
    """Create hooks dict for ClaudeAgentOptions.

    Args:
        dangerous_commands: Optional list of additional dangerous patterns.
            If provided, these are combined with DANGEROUS_PATTERNS.
            If None, only DANGEROUS_PATTERNS are used.

    Returns:
        A dict with HookMatcher format suitable for ClaudeAgentOptions.
    """
    if dangerous_commands is None:
        hook = check_dangerous_command
    else:
        combined_patterns = list(DANGEROUS_PATTERNS) + dangerous_commands
        hook = create_dangerous_command_hook(combined_patterns)

    return {
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[hook]),
        ],
    }

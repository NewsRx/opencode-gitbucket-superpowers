#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session initialization script for AI agents.

Extracts git context needed for agent startup:
- DEV_NAME: Developer's git config name (for commit trailers)
- DEV_EMAIL: Developer's git config email (for commit trailers)
- GIT_OWNER: Repository owner (for GitHub/GitBucket API calls)
- GIT_REPO: Repository name (for GitHub/GitBucket API calls)
- GIT_HOOKS_PATH: Git hooks path (to verify hooks installed)
- GIT_REMOTE_URL: Full remote URL (for reference)
- GIT_PLATFORM: github, gitbucket, or unknown
- GITBUCKET_URL: GitBucket base URL (if GitBucket detected)
- GITBUCKET_HAS_CREDENTIALS: true/false (if credentials in .env)

Usage:
    uv run scripts/session_init.py

Exit codes:
    0: Success
    1: No remote configured
    2: Non-git remote detected

Can also be run directly with Python 3.11+:
    python scripts/session_init.py

The script self-boots with no external dependencies.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse


class GitContext(NamedTuple):
    """Git context extracted from repository."""

    dev_name: str
    dev_email: str
    hooks_path: str
    remote_url: str
    platform: str  # github, gitbucket, or unknown
    owner: str | None
    repo: str | None
    gitbucket_url: str | None
    gitbucket_has_credentials: bool


def run_git_command(args: list[str]) -> str | None:
    """Run a git command and return output, or None if failed."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def get_user_name() -> str:
    """Get git user name or fallback to $USER."""
    name = run_git_command(["config", "user.name"])
    if name:
        return name
    return os.environ.get("USER", "unknown")


def get_user_email() -> str:
    """Get git user email or fallback to $USER@$HOSTNAME."""
    email = run_git_command(["config", "user.email"])
    if email:
        return email
    user = os.environ.get("USER", "unknown")
    hostname = os.environ.get("HOSTNAME", "localhost")
    return f"{user}@{hostname}"


def get_hooks_path() -> str:
    """Get git hooks path or empty string if not configured."""
    hooks = run_git_command(["config", "core.hooksPath"])
    return hooks or ""


def get_remote_url() -> str | None:
    """Get origin remote URL or None if not configured."""
    return run_git_command(["remote", "get-url", "origin"])


def parse_github_url(url: str) -> tuple[str, str] | tuple[None, None]:
    """Parse owner and repo from GitHub remote URL.

    Supports:
    - SSH: git@github.com:owner/repo.git
    - HTTPS: https://github.com/owner/repo.git

    Returns:
        (owner, repo) on success, (None, None) on failure
    """
    # SSH format: git@github.com:owner/repo.git
    ssh_pattern = r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.match(ssh_pattern, url)
    if match:
        return match.group(1), match.group(2)

    # HTTPS format: https://github.com/owner/repo.git
    https_pattern = r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.match(https_pattern, url)
    if match:
        return match.group(1), match.group(2)

    return None, None


def parse_gitbucket_url(url: str) -> tuple[str, str, str] | tuple[None, None, None]:
    """Parse base URL, owner, and repo from GitBucket remote URL.

    Supports:
    - SSH: ssh://git@hostname:port/owner/repo.git
    - SSH: git@hostname:owner/repo.git (no port)
    - HTTPS: https://hostname/owner/repo.git

    Returns:
        (base_url, owner, repo) on success, (None, None, None) on failure
    """
    # SSH format: ssh://git@hostname:port/owner/repo.git
    ssh_url_pattern = r"^ssh://git@([^:/]+):(\d+)/([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.match(ssh_url_pattern, url)
    if match:
        host = match.group(1)
        owner = match.group(3)
        repo = match.group(4)
        base_url = f"https://{host}/gitbucket/"
        return base_url, owner, repo

    # SSH format: git@hostname:owner/repo.git (no port, colon separator)
    ssh_short_pattern = r"^git@([^:]+):([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.match(ssh_short_pattern, url)
    if match:
        host = match.group(1)
        # Skip if this is actually github.com
        if host == "github.com":
            return None, None, None
        owner = match.group(2)
        repo = match.group(3)
        base_url = f"https://{host}/gitbucket/"
        return base_url, owner, repo

    # HTTPS format: https://hostname/owner/repo.git
    https_pattern = r"^https://([^/]+)/([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.match(https_pattern, url)
    if match:
        host = match.group(1)
        # Skip if this is actually github.com
        if host == "github.com":
            return None, None, None
        owner = match.group(2)
        repo = match.group(3)
        base_url = f"https://{host}/gitbucket/"
        return base_url, owner, repo

    return None, None, None


def check_gitbucket_credentials() -> bool:
    """Check if GitBucket credentials exist in .env file.

    Looks for .env in the repository root (relative to this script).

    Returns:
        True if both GITBUCKET_URL and GITBUCKET_TOKEN found, False otherwise
    """
    try:
        # Get repo root relative to this script
        script_path = Path(__file__).resolve()
        env_path = script_path.parent.parent / ".env"

        if env_path.exists():
            content = env_path.read_text()
            return "GITBUCKET_TOKEN=" in content and "GITBUCKET_URL=" in content
    except (IOError, OSError):
        pass

    return False


def is_github_remote(url: str) -> bool:
    """Check if remote URL is a GitHub remote by extracting hostname.

    Properly parses URL to check hostname, avoiding substring matching issues.
    """
    # Handle SSH format: git@github.com:owner/repo.git
    if url.startswith("git@"):
        match = re.match(r"^git@([^:]+):", url)
        if match:
            hostname = match.group(1)
            return hostname == "github.com"

    # Handle HTTPS format: https://github.com/owner/repo.git
    try:
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname == "github.com"
    except Exception:
        pass

    return False


def extract_git_context() -> GitContext | None:
    """Extract git context from repository.

    Returns:
        GitContext on success, None if no remote configured
    """
    remote_url = get_remote_url()
    if not remote_url:
        return None

    user_name = get_user_name()
    user_email = get_user_email()
    hooks_path = get_hooks_path()

    # Check if GitHub remote (properly validated)
    if is_github_remote(remote_url):
        owner, repo = parse_github_url(remote_url)
        if owner and repo:
            return GitContext(
                dev_name=user_name,
                dev_email=user_email,
                hooks_path=hooks_path,
                remote_url=remote_url,
                platform="github",
                owner=owner,
                repo=repo,
                gitbucket_url=None,
                gitbucket_has_credentials=False,
            )

    # GitBucket remote (non-GitHub git remote)
    base_url, owner, repo = parse_gitbucket_url(remote_url)
    if base_url and owner and repo:
        has_creds = check_gitbucket_credentials()
        return GitContext(
            dev_name=user_name,
            dev_email=user_email,
            hooks_path=hooks_path,
            remote_url=remote_url,
            platform="gitbucket",
            owner=owner,
            repo=repo,
            gitbucket_url=base_url,
            gitbucket_has_credentials=has_creds,
        )

    # Unknown remote type
    return GitContext(
        dev_name=user_name,
        dev_email=user_email,
        hooks_path=hooks_path,
        remote_url=remote_url,
        platform="unknown",
        owner=None,
        repo=None,
        gitbucket_url=None,
        gitbucket_has_credentials=False,
    )


def format_output(ctx: GitContext) -> str:
    """Format git context for output."""
    lines = [
        "# Session Init - Git Context",
        f"DEV_NAME={ctx.dev_name}",
        f"DEV_EMAIL={ctx.dev_email}",
        f"GIT_HOOKS_PATH={ctx.hooks_path}",
        f"GIT_REMOTE_URL={ctx.remote_url}",
    ]

    if ctx.platform == "github":
        lines.extend(
            [
                f"GIT_OWNER={ctx.owner}",
                f"GIT_REPO={ctx.repo}",
                "GIT_PLATFORM=github",
                "",
                "# GitHub Repository Detected",
                "# Use GitHub tools (github_create_issue, github_issue_write, etc.) for issue tracking",
            ]
        )

    elif ctx.platform == "gitbucket":
        lines.extend(
            [
                f"GIT_OWNER={ctx.owner}",
                f"GIT_REPO={ctx.repo}",
                "GIT_PLATFORM=gitbucket",
                f"GITBUCKET_URL={ctx.gitbucket_url}",
                f"GITBUCKET_HAS_CREDENTIALS={'true' if ctx.gitbucket_has_credentials else 'false'}",
                "",
                "# GitBucket Repository Detected",
                "# Use GitBucket tools (gitbucket_create_issue, etc.) for issue tracking",
            ]
        )

        if not ctx.gitbucket_has_credentials:
            lines.extend(
                [
                    "# WARNING: GITBUCKET_URL and/or GITBUCKET_TOKEN not found in .env",
                    "# Set these credentials for GitBucket API access",
                ]
            )

    else:  # unknown
        lines.append("GIT_PLATFORM=unknown")

    return "\n".join(lines)


def main() -> int:
    """Extract and output git context."""
    ctx = extract_git_context()

    if ctx is None:
        print("ERROR: No git remote configured", file=sys.stderr)
        print("Run: git remote add origin <url>", file=sys.stderr)
        return 1

    if ctx.platform == "unknown":
        print("WARNING: Unknown remote type", file=sys.stderr)
        print(f"Remote URL: {ctx.remote_url}", file=sys.stderr)

    print(format_output(ctx))
    return 0


if __name__ == "__main__":
    sys.exit(main())

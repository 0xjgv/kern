#!/usr/bin/env python3
"""kern - Autonomous 3-stage development pipeline using claude-agent-sdk."""

import argparse
import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    query,
)

# === Security: Tool Lists for Least-Privilege Stages ===

READ_ONLY_TOOLS = [
    "Read",
    "Glob",
    "Grep",
    "LS",
    "TaskGet",
    "TaskUpdate",
    "TaskList",
    "TaskCreate",
]

READ_WRITE_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "LS",
    "Bash",
    "TaskGet",
    "TaskUpdate",
    "TaskList",
    "TaskCreate",
    "Task",
]

# === Security: Injection Detection ===

# Suspicious patterns indicating prompt injection attempts
INJECTION_PATTERNS = re.compile(
    r"ignore.*(previous|all).*instructions|"
    r"disregard.*above|"
    r"</(system|user)>",
    re.IGNORECASE,
)

MAX_HINT_LENGTH = 500


def validate_hint(hint: str) -> None:
    """Validate hint - reject prompt injection patterns.

    Raises:
        ValueError: If hint is too long or contains suspicious patterns.
    """
    if len(hint) > MAX_HINT_LENGTH:
        raise ValueError(f"Hint too long (max {MAX_HINT_LENGTH} chars)")
    if INJECTION_PATTERNS.search(hint):
        raise ValueError("Hint contains suspicious pattern")


def wrap_untrusted(source: str, content: str) -> str:
    """Wrap content to mark as untrusted data.

    Args:
        source: Label identifying the data source (e.g., "hint", "git-diff").
        content: The untrusted content to wrap.

    Returns:
        Content wrapped in <data source="..."> tags.
    """
    return f'<data source="{source}">\n{content}\n</data>'


# === Security: Stage-Specific Options ===


def get_stage_options(stage_num: int, model: str = "opus") -> ClaudeAgentOptions:
    """Return appropriate options for each stage.

    - Stages 0, 1, 3: Read-only (research, planning, commit review)
    - Stage 2: Read-write (implementation)

    Args:
        stage_num: Stage number (0-3).
        model: Model to use ("opus", "haiku", etc.).

    Returns:
        ClaudeAgentOptions configured for the stage.
    """
    if stage_num == 2:
        # Implementation stage needs write access
        return ClaudeAgentOptions(
            model=model,
            allowed_tools=READ_WRITE_TOOLS,
            permission_mode="bypassPermissions",
        )
    # Research/commit stages are read-only
    return ClaudeAgentOptions(
        model=model,
        allowed_tools=READ_ONLY_TOOLS,
        permission_mode="bypassPermissions",
    )


# === Git Utilities ===


def git_project_id() -> str:
    """Get project name from git root."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return Path(root).name
    except subprocess.CalledProcessError:
        return Path.cwd().name


def git_branch_safe() -> str:
    """Get branch name, sanitized (/ replaced with -)."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return branch.replace("/", "-")
    except subprocess.CalledProcessError:
        return "unknown"


def git_diff_stat() -> str:
    """Get diff statistics."""
    try:
        return subprocess.check_output(
            ["git", "diff", "--stat"],
            stderr=subprocess.DEVNULL,
            text=True,
        )[:1000]
    except subprocess.CalledProcessError:
        return ""


def git_recent_commits(count: int = 5, max_chars: int = 2000) -> str:
    """Get recent commit log with stats."""
    try:
        result = subprocess.check_output(
            ["git", "log", f"-{count}", "--format=[%h] %s%n%b", "--stat"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return result[:max_chars]
    except subprocess.CalledProcessError:
        return "No commits yet"


def has_changes() -> bool:
    """Check if there are uncommitted changes."""
    staged = (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
            check=False,
        ).returncode
        != 0
    )
    unstaged = (
        subprocess.run(
            ["git", "diff", "--quiet"],
            capture_output=True,
            check=False,
        ).returncode
        != 0
    )
    return staged or unstaged


# === Prompt Templates ===

STAGE_0_PROMPT = """
# Stage 0: Populate Task Queue

Parse SPEC.md and create tasks in the queue idempotently.

## Context
SPEC File: {spec_file}

## Instructions
1. **Read SPEC.md**: Get all items with `[ ]` (pending) or `[~]` (in-progress)
2. **Check Existing Tasks**: `TaskList` to see current queue
3. **Create Missing Tasks**: For each SPEC item not in queue:
   - `TaskCreate` with:
     - subject: First 80 chars of task description
     - description: Full task text
     - metadata.spec_line: Line number in SPEC.md
     - metadata.spec_status: `pending` or `in_progress`
   - Skip if task with same `spec_line` already exists
4. **Output**: Print `SUCCESS created=N existing=M` where N=new, M=existed
"""

STAGE_1_PROMPT = """
# Stage 1: Research and Plan

Research the codebase and create an implementation plan.

## Context
Task ID: {task_id}
{hint}

### Recent Commits
{recent_commits}

## Instructions
1. **Get Task**:
   - If `{task_id}` provided: `TaskGet` with ID `{task_id}`
   - Otherwise: `TaskList`, select first task with status `pending` or `in_progress`
     - Mark it `in_progress` via `TaskUpdate`
     - Mark corresponding SPEC.md line `[~]` using `metadata.spec_line`

2. **Research**: Use agents to explore the codebase in parallel:
   - `codebase-analyzer`: Understand current vs desired state
   - `codebase-pattern-finder`: Identify patterns
   - `codebase-locator`: Find relevant files
   - `web-search-researcher`: Search the web for relevant information (optional)

3. **Store Findings**: `TaskUpdate` with metadata:
   - `metadata.research.files`: Array of file paths
   - `metadata.research.pattern`: Pattern to follow
   - `metadata.research.constraints`: Array of constraints
   - `metadata.plan`: Array of implementation steps

4. **Output**: Print `SUCCESS task_id=<ID>` or `FAILED: <reason>`
   - If no tasks in queue: Print `SUCCESS task_id=none`
"""

STAGE_2_PROMPT = """
# Stage 2: Implement

Implement the task based on research findings.

## Context
Task ID: {task_id}
{hint}

### Recent Commits
{recent_commits}

## Instructions
1. **Get Task**: `TaskGet` with ID `{task_id}` — metadata has research and plan

2. **Implement**: Follow the plan from metadata, creating tasks for each step:
   - Create tasks for each step
   - Modify files in order specified by the tasks
   - Keep changes minimal and focused
   - Follow the identified pattern
   - Respect constraints

3. **Validate**: Run `make check` or appropriate validation

4. **Store Implementation Details**: `TaskUpdate` with metadata:
   - `metadata.implementation.files_changed`: Array of file paths that were changed
   - `metadata.implementation.validation`: Validation result

5. **Output**: Print `SUCCESS` or `FAILED: <reason>`
"""

STAGE_3_PROMPT = """
# Stage 3: Review and Commit

Review changes and commit.

## Context
Task ID: {task_id}

### Recent Commits
{recent_commits}

### Changes
{diff}

## Instructions
1. **Get Task**: `TaskGet` with ID `{task_id}` for context

2. **Review Changes**: `git diff` to verify — fix debug prints, typos, secrets

3. **Commit**:
   ```bash
   git add <specific files>
   git commit -m "$(cat <<'EOF'
   [kern] task: <subject line>
   <description>

   What changed:
    - <what was done>

   Validation:
    - <validation result>
   EOF
   )"
   ```

4. **Mark Task as Completed**: `TaskUpdate` with `status: completed`

5. **Sync SPEC.md**: Mark task `[x]` in SPEC.md

6. **Capture Learnings**: Note non-obvious patterns discovered

7. **Output**: Print `SUCCESS` or `FAILED: <reason>`
"""


# === Secure Prompt Building ===


def build_prompt(
    template: str,
    task_id: str = "",
    hint: str = "",
    spec_file: str = "SPEC.md",
) -> str:
    """Build prompt with wrapped untrusted data.

    Note: Python f-strings don't need awk-style escaping.
    We wrap external data with <data> tags for transparency.

    Args:
        template: Prompt template with placeholders.
        task_id: Task ID to substitute.
        hint: User hint (will be validated and wrapped).
        spec_file: SPEC file path.

    Returns:
        Formatted prompt with wrapped untrusted data.
    """
    diff = wrap_untrusted("git-diff", git_diff_stat())
    commits = wrap_untrusted("git-log", git_recent_commits())
    wrapped_hint = wrap_untrusted("hint", hint) if hint else ""

    return template.format(
        task_id=task_id,
        hint=wrapped_hint,
        diff=diff,
        recent_commits=commits,
        spec_file=spec_file,
    )


# === Stage Execution ===


def _extract_text_blocks(message: AssistantMessage) -> list[str]:
    """Extract text content from assistant message blocks."""
    return [block.text for block in message.content if isinstance(block, TextBlock)]


def _extract_task_id(text: str) -> str | None:
    """Extract task_id from stage output text."""
    match = re.search(r"task_id=(\d+|none)", text)
    if match:
        task_id = match.group(1)
        return None if task_id == "none" else task_id
    return None


async def run_stage(
    stage_num: int,
    name: str,
    prompt: str,
    model: str = "opus",
    verbose: bool = False,
) -> tuple[bool, str | None]:
    """Execute a single stage with appropriate permissions.

    Args:
        stage_num: Stage number (0-3).
        name: Human-readable stage name.
        prompt: Prompt to send to Claude.
        model: Model to use.
        verbose: If True, print assistant output.

    Returns:
        Tuple of (success, task_id) where task_id is extracted from Stage 1.
    """
    print(f"[{stage_num}] {name}")
    options = get_stage_options(stage_num, model)

    success = False
    extracted_task_id = None

    try:
        async for message in query(prompt=prompt, options=options):
            if not isinstance(message, AssistantMessage):
                continue

            texts = _extract_text_blocks(message)
            if verbose:
                for text in texts:
                    print(text)

            for text in texts:
                if "FAILED:" in text:
                    print(f"Stage {stage_num} failed: {text}")
                    return False, None
                if "SUCCESS" in text:
                    success = True
                    if stage_num == 1:
                        extracted_task_id = _extract_task_id(text)

        return success, extracted_task_id
    except Exception as e:
        print(f"Stage {stage_num} error: {e}")
        return False, None


async def run_stage_0(
    spec_file: str = "SPEC.md",
    verbose: bool = False,
) -> bool:
    """Stage 0: Populate task queue from SPEC.md."""
    prompt = build_prompt(STAGE_0_PROMPT, spec_file=spec_file)
    success, _ = await run_stage(
        0, "Populate Task Queue", prompt, model="haiku", verbose=verbose
    )
    return success


async def run_task(
    task_id: str | None = None,
    hint: str = "",
    verbose: bool = False,
) -> tuple[bool, str | None]:
    """Execute stages 1-3 for a single task.

    Args:
        task_id: Optional task ID. If None, Stage 1 selects from queue.
        hint: User hint for the task.
        verbose: If True, print verbose output.

    Returns:
        Tuple of (success, task_id) where task_id may be selected by Stage 1.
    """
    # Stage 1: Research & Planning
    prompt_1 = build_prompt(
        STAGE_1_PROMPT,
        task_id=task_id or "",
        hint=hint,
    )
    success, selected_task_id = await run_stage(
        1, "Research & Planning", prompt_1, model="opus", verbose=verbose
    )
    if not success:
        return False, None

    # Use task_id from Stage 1 if we didn't have one
    task_id = task_id or selected_task_id
    if not task_id:
        print("No tasks in queue")
        return True, None  # Success but no work to do

    print(f"Working on task: {task_id}")

    # Stage 2: Implement
    prompt_2 = build_prompt(
        STAGE_2_PROMPT,
        task_id=task_id,
        hint=hint,
    )
    success, _ = await run_stage(
        2, "Implement", prompt_2, model="opus", verbose=verbose
    )
    if not success:
        return False, task_id

    # Stage 3: Commit (only if changes exist)
    if has_changes():
        prompt_3 = build_prompt(
            STAGE_3_PROMPT,
            task_id=task_id,
        )
        success, _ = await run_stage(
            3, "Commit & Review", prompt_3, model="haiku", verbose=verbose
        )
        if not success:
            return False, task_id
    else:
        print("No changes to commit")

    print(f"Task {task_id} completed")
    return True, task_id


async def run_pipeline(
    task_id: str | None = None,
    hint: str = "",
    max_tasks: int = 5,
    verbose: bool = False,
) -> bool:
    """Execute the full 4-stage pipeline.

    Two modes:
    - Single task mode: If task_id provided, run stages 1-3 for that task
    - Iteration mode: If no task_id, run stage 0 then iterate stages 1-3

    Args:
        task_id: Optional task ID for single-task mode.
        hint: User hint for the task.
        max_tasks: Maximum tasks to process in iteration mode.
        verbose: If True, print verbose output.

    Returns:
        True if pipeline completed successfully.
    """
    # Set task list scope
    project_id = git_project_id()
    branch = git_branch_safe()
    os.environ["CLAUDE_CODE_TASK_LIST_ID"] = f"kern-{project_id}-{branch}"
    os.environ["CLAUDE_CODE_ENABLE_TASKS"] = "true"

    if task_id:
        # Single task mode
        print(f"Executing task: {task_id}")
        success, _ = await run_task(task_id, hint, verbose)
        return success

    # Iteration mode
    # Stage 0: Populate task queue from SPEC.md
    if not await run_stage_0(verbose=verbose):
        print("Failed to populate task queue")
        return False

    # Process tasks from queue
    task_count = 0
    while task_count < max_tasks:
        success, completed_task_id = await run_task(
            task_id=None, hint=hint, verbose=verbose
        )

        if not success:
            if completed_task_id:
                print(f"Task {completed_task_id} failed")
                return False
            break  # No more tasks

        if completed_task_id is None:
            break  # No more tasks in queue

        task_count += 1

    if task_count == 0:
        print("No pending tasks in queue")
    else:
        print(f"Completed {task_count} task(s)")

    return True


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="kern - Autonomous development pipeline"
    )
    parser.add_argument(
        "task_id", nargs="?", default=None, help="Task ID to execute (optional)"
    )
    parser.add_argument("--hint", "-H", default="", help="Hint for the task")
    parser.add_argument(
        "--count", "-c", type=int, default=5, help="Max tasks to process (default: 5)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Dry run (not implemented)"
    )
    args = parser.parse_args()

    # Validate hint early (fail fast)
    if args.hint:
        try:
            validate_hint(args.hint)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        print("[DRY-RUN] Would run pipeline")
        print(f"  Task ID: {args.task_id or '(auto-select)'}")
        print(f"  Hint: {args.hint or '(none)'}")
        print(f"  Max tasks: {args.count}")
        sys.exit(0)

    success = asyncio.run(
        run_pipeline(
            args.task_id,
            args.hint,
            args.count,
            args.verbose,
        )
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

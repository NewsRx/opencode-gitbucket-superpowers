---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Store plans as issues:** Plans are stored in GitHub/GitBucket issues (not local files). Check `GIT_PLATFORM` from session context and use appropriate issue creation tool.

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## After the Plan

**Create Plan Issue (REQUIRED):**

Plans are stored as GitHub/GitBucket issues. No local file storage.

**MCP Availability Gate (BEFORE creating issue):**

Check `GIT_PLATFORM` in your session context (`<GIT_CONTEXT>` block):

- If `GIT_PLATFORM=github`:
  - GitHub MCP available → Proceed with github_issue_write

- Else if `GIT_PLATFORM=gitbucket`:
  ```markdown
  Check GITBUCKET_HAS_CREDENTIALS:
  - If false: STOP. Tell user "GitBucket credentials required. Set GITBUCKET_URL and GITBUCKET_TOKEN in .env, then restart session."
  - If true: Proceed with gitbucket_create_issue
  ```

- Else (unknown):
  ```markdown
  STOP. Tell user:
  ```
  FATAL: Cannot create plan - no issue tracking available
  
  Plans must be tracked in GitHub/GitBucket issues for:
  - Persistent storage
  - Team visibility
  - Progress tracking
  
  Options:
  1. Add GitHub remote: git remote add origin https://github.com/user/repo.git
  2. Add GitBucket credentials to .env (GITBUCKET_URL, GITBUCKET_TOKEN)
  3. Restart session to re-detect platform
  
  Cannot proceed without issue tracking.
  ```

**Create Plan Issue (after gate passes):**

The issue body should contain the complete plan with:
- All tasks
- All steps
- Complete code blocks

Use the following:

- If GitHub:
  ```markdown
  Use github_issue_write with:
  - method: "create"
  - title: [Plan] <feature-name> Implementation
  - body: Full implementation plan (all sections, complete content)
  - labels: plan
  ```

- If GitBucket:
  ```markdown
  Use gitbucket_create_issue with:
  - title: [Plan] <feature-name> Implementation
  - body: Full implementation plan (all sections, complete content)
  - labels: plan
  ```

**Link to Spec Issue:**

Comment on the spec issue to link this plan:

- If GitHub: `github_add_issue_comment(spec_issue_number, "Implementation plan: #<plan_issue_number>")`
- If GitBucket: `gitbucket_add_issue_comment(spec_issue_number, "Implementation plan: #<plan_issue_number>")`

**No Local File Storage:**

Plans are NOT stored in `docs/superpowers/plans/`. They live only as issues.

**Why Halt Instead of Fallback:**

File-based plans are **not acceptable** because:
- No team visibility
- No persistent tracking
- Lost on developer machine
- No integration with workflow

**MCP availability is a hard requirement.** Halt with clear remediation steps.

- If GitHub: `github_add_issue_comment(spec_issue_number, "Implementation plan: #<plan_issue_number>")`
- If GitBucket: `gitbucket_add_issue_comment(spec_issue_number, "Implementation plan: #<plan_issue_number>")`

## Self-Review

After writing the complete plan, review with fresh eyes:

**1. Spec coverage:** Skim each section/requirement in the spec issue. Can you point to a task that implements it? Edit the plan issue to add missing tasks.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Edit the issue to fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug. Edit to fix.

Fix issues by editing the plan issue. No need to re-review — just fix and move on.

## Execution Handoff

After creating the plan issue, offer execution choice:

**"Plan created as issue #<number>. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development
- Fresh subagent per task + two-stage review

**If Inline Execution chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:executing-plans
- Batch execution with checkpoints for review

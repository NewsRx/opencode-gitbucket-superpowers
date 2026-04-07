# Platform Detection (GitBucket vs GitHub)

Skills that interact with issue tracking, specs, and plans must detect which platform is available and adapt accordingly.

## Automatic Detection at Session Start

When an agent session starts, the plugin automatically runs `scripts/session_init.py` which:

1. **Extracts git remote URL** from `git remote get-url origin`
2. **Detects platform** from URL pattern:
   - URLs containing `github.com` → `GIT_PLATFORM=github`
   - All other git URLs → `GIT_PLATFORM=gitbucket`
3. **Parses owner/repo** for API calls
4. **Checks credentials** for GitBucket (`.env` file for `GITBUCKET_URL` and `GITBUCKET_TOKEN`)
5. **Injects context** into agent session:
   ```
   <GIT_CONTEXT>
   DEV_NAME=...
   DEV_EMAIL=...
   GIT_OWNER=...
   GIT_REPO=...
   GIT_PLATFORM=github|gitbucket|unknown
   GITBUCKET_URL=... (if GitBucket)
   GITBUCKET_HAS_CREDENTIALS=true|false (if GitBucket)
   </GIT_CONTEXT>
   ```

## Skill Integration Pattern

Skills MUST use the detected platform to create issues:

```markdown
### In the agent context:

Check <GIT_CONTEXT> for GIT_PLATFORM:
- github → Use GitHub tools (github_issue_write, github_create_pull_request, etc.)
- gitbucket → Use GitBucket tools (gitbucket_create_issue, gitbucket_create_pull_request, etc.)

For GitBucket:
- Check GITBUCKET_HAS_CREDENTIALS
- If false, STOP and warn user to set GITBUCKET_URL and GITBUCKET_TOKEN in .env
- Do not proceed until credentials are configured

All specs, plans, and bug reports are stored as issues. No local file fallback.
```

## Branch Workflow Detection

**Automatic at session start:**

The plugin detects and configures the branch workflow:

1. **Detect production branch:**
   ```bash
   # Try origin/HEAD first
   PRODUCTION_BRANCH=$(git rev-parse --abbrev-ref origin/HEAD 2>/dev/null | sed 's|origin/||')
   
   # Fallback to common names
   if [ -z "$PRODUCTION_BRANCH" ]; then
     for branch in main master; do
       if git show-ref --verify --quiet refs/remotes/origin/$branch; then
         PRODUCTION_BRANCH=$branch
         break
       fi
     done
   fi
   ```

2. **If production branch cannot be detected:**
   - Halt session with error: "Cannot detect production branch. Set origin/HEAD with: `git remote set-head origin <your-main-branch>`"
   - Suggest adding `branch-workflow: feature|dev|<branch>` to CLAUDE.md or AGENTS.md

3. **Read branch-workflow configuration:**
   - Parse CLAUDE.md/AGENTS.md for `branch-workflow: <prefix>|<integration>|<production>`
   - Format: `<feature-prefix>|<integration-branch>|<production-branch>`
   - Example: `branch-workflow: feature|dev|newsrx`

4. **Default workflow:**
   - If no configuration: use `feature|dev|<PRODUCTION_BRANCH>`
   - Feature prefix: `feature` (or configured prefix)
   - Integration branch: `dev` (or configured integration branch)
   - Production branch: detected from origin/HEAD or configuration

5. **Create integration branch if missing:**
   ```bash
   INTEGRATION_BRANCH="dev"  # default
   CONFIGURED_WORKFLOW=$(grep "branch-workflow:" CLAUDE.md AGENTS.md 2>/dev/null)
   
   if [ -n "$CONFIGURED_WORKFLOW" ]; then
     INTEGRATION_BRANCH=$(echo "$CONFIGURED_WORKFLOW" | cut -d'|' -f2)
   fi
   
   # Create if missing
   if ! git show-ref --verify --quiet refs/heads/$INTEGRATION_BRANCH; then
     if [ -n "$PRODUCTION_BRANCH" ]; then
       git branch $INTEGRATION_BRANCH $PRODUCTION_BRANCH
       echo "Created '$INTEGRATION_BRANCH' branch from '$PRODUCTION_BRANCH'"
       # Push to remote if origin exists
       git push -u origin $INTEGRATION_BRANCH 2>/dev/null || true
     fi
   fi
   ```

6. **Inject into session context:**
   ```
   <GIT_CONTEXT>
   ...
   GIT_WORKFLOW_PREFIX=feature
   GIT_INTEGRATION_BRANCH=dev
   GIT_PRODUCTION_BRANCH=<detected>
   </GIT_CONTEXT>
   ```

**Examples:**

| Repo State | Detection Result |
|-----------|------------------|
| origin/HEAD set | Production branch from origin/HEAD |
| No origin/HEAD, has origin/main | Production = main |
| No origin/HEAD, has origin/master | Production = master |
| Custom main branch (newsrx) | If origin/HEAD → origin/newsrx, detected correctly |
| No remote branches | Halt with error, suggest configuration |

## File Migration to Issues

**On session start (after platform detected):**

If GitHub or GitBucket MCP available:

1. **Discover existing files:**
   ```bash
   find docs/superpowers/specs -name "*.md" -type f 2>/dev/null
   find docs/superpowers/plans -name "*.md" -type f 2>/dev/null
   ```

2. **For each spec file:**
   ```markdown
   If GIT_PLATFORM=github:
     - Parse title from first `# ` header
     - Use github_issue_write with:
       - title: `[Spec] <parsed-title>`
       - body: File content + "\n\nMigrated from: `docs/superpowers/specs/<filename>.md`"
       - labels: spec
   
   If GIT_PLATFORM=gitbucket:
     - Parse title from first `# ` header
     - Use gitbucket_create_issue with:
       - title: `[Spec] <parsed-title>`
       - body: File content + "\n\nMigrated from: `docs/superpowers/specs/<filename>.md`"
       - labels: spec
   ```

3. **For each plan file:**
   ```markdown
   If GIT_PLATFORM=github:
     - Parse title from first `# ` header
     - Use github_issue_write with:
       - title: `[Plan] <parsed-title>`
       - body: File content + "\n\nMigrated from: `docs/superpowers/plans/<filename>.md`"
       - labels: plan
   
   If GIT_PLATFORM=gitbucket:
     - Parse title from first `# ` header
     - Use gitbucket_create_issue with:
       - title: `[Plan] <parsed-title>`
       - body: File content + "\n\nMigrated from: `docs/superpowers/plans/<filename>.md`"
       - labels: plan
   ```

4. **On successful issue creation:**
   ```bash
   # Create archive directory if missing
   mkdir -p docs/superpowers/archive
   
   # Move file to archive
   mv docs/superpowers/specs/<filename>.md docs/superpowers/archive/<filename>.md
   ```

5. **Add archive comment to issue:**
   ```markdown
   Add comment: "Archived original: `docs/superpowers/archive/<filename>.md`"
   ```

6. **Report to dev:**
   ```
   Migrated <N> specs, <M> plans to GitHub/GitBucket issues.
   Originals archived in docs/superpowers/archive/
   ```

**Error handling:**
- File has no title header → use filename as title
- Issue already exists (title match) → skip, don't duplicate
- Archive directory missing → create it
- Migration fails → log error, continue session, leave file in place
- Platform unknown → skip migration (file-based workflow continues)

**Migration runs once:** Only on first session start after MCP available.

## Example: Creating a Spec Issue

```markdown
After brainstorming, create a spec issue:

Check GIT_PLATFORM from session context:

If GIT_PLATFORM=github:
  Use github_issue_write with:
  - title: [Spec] <topic>
  - body: Full design specification (all sections, complete content)
  - labels: spec, plus relevant feature labels

If GIT_PLATFORM=gitbucket:
  Check GITBUCKET_HAS_CREDENTIALS:
  - If false: STOP. Tell user "GitBucket credentials required. Set GITBUCKET_URL and GITBUCKET_TOKEN in .env"
  - If true: Proceed with gitbucket_create_issue

  Use gitbucket_create_issue with:
  - title: [Spec] <topic>
  - body: Full design specification (all sections, complete content)
  - labels: spec, plus relevant feature labels

If GIT_PLATFORM=unknown:
  STOP. Tell user "No GitHub/GitBucket remote detected. Configure git remote to enable spec tracking."

Never write specs to local files. Only issues.
```
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
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
# Branch Protection Rules for Cardea

This document outlines the recommended branch protection rules for the `main` branch.

## Required Status Checks

Enable the following status checks to pass before merging:

### Required (Must Pass)
- `✅ PR Status Check` - Final gate that aggregates all CI results
- `🔮 Oracle - Lint & Type Check` (when oracle/* changed)
- `🛡️ Sentry - Lint & Type Check` (when sentry/* changed)
- `🎨 Dashboard - Lint & Type Check` (when dashboard/* changed)

### Recommended (Should Pass)
- `🔮 Oracle - Docker Build`
- `🛡️ Sentry - Docker Build`
- `🎨 Dashboard - Build`
- `🔒 Security Scan`

## GitHub Settings

To configure branch protection, go to:
**Settings → Branches → Add branch protection rule**

### Recommended Settings for `main`:

```yaml
Branch name pattern: main

Protect matching branches:
  ✅ Require a pull request before merging
    ✅ Require approvals: 1
    ✅ Dismiss stale pull request approvals when new commits are pushed
    ✅ Require review from Code Owners
  
  ✅ Require status checks to pass before merging
    ✅ Require branches to be up to date before merging
    Status checks that are required:
      - "✅ PR Status Check"
  
  ✅ Require conversation resolution before merging
  
  ✅ Require signed commits (optional but recommended)
  
  ✅ Require linear history (optional - enforces squash/rebase)
  
  ❌ Allow force pushes (keep disabled)
  ❌ Allow deletions (keep disabled)

  ✅ Lock branch (for releases only)
```

## Quick Setup via GitHub CLI

```bash
# Install GitHub CLI if not present
# brew install gh  # or apt install gh

# Configure branch protection
gh api -X PUT /repos/gauciv/cardea/branches/main/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["✅ PR Status Check"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
EOF
```

## Environment-Specific Branches

| Branch | Protection Level | Required Checks |
|--------|-----------------|-----------------|
| `main` | Strict | All CI + Review |
| `develop` | Moderate | Lint + Build |
| `feature/*` | None | None |
| `hotfix/*` | Moderate | Lint + Security |

## Merge Strategies

Recommended merge strategy: **Squash and merge**

This keeps the commit history clean and makes it easier to:
- Revert changes if needed
- Understand what each PR accomplished
- Generate changelogs automatically

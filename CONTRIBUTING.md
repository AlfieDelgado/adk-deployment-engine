# Contributing & Git Workflow

This document explains the git workflow and branching strategy for this project.

---

## Branch Strategy

| Branch | Purpose | Environment |
|--------|---------|-------------|
| `main` | Production-ready code | Production |
| `dev` | Integration testing | Development |
| `stag` | Pre-production staging | Staging |
| `feat/*` | Feature development | - |
| `fix/*` | Bug fixes | - |

---

## Creating a Feature Branch

Choose a base branch based on your goal:

| Base Branch | Use For | Example Target |
|-------------|---------|----------------|
| `dev` | New features, standard workflow | PR to `dev` |
| `main` | Hotfixes, production-ready changes | PR to `main` |
| `stag` | Pre-production validation | PR to `stag` |

```bash
# From your chosen base branch
git checkout <base-branch>  # dev, main, or stag

# Create and switch to feature branch
git checkout -b feat/your-feature-name

# Or for bug fixes
git checkout -b fix/your-bug-fix

# Or for hotfixes to production
git checkout -b hotfix/critical-issue
```

---

## Making Changes

```bash
# Make your changes and commit
git add .
git commit -m "feat: add new feature"

# Or use conventional commits
git commit -m "fix: resolve deployment issue"
git commit -m "docs: update README"
git commit -m "chore: upgrade dependencies"
```

**Conventional Commit Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring
- `test:` - Test additions/changes

---

## Merging Strategy

### Rebase and Merge (Project Standard)

This repository uses **rebase and merge** for all pull requests. This is enforced through branch protection rules.

**GitHub PR:**
1. Create PR from `feat/*` to `dev`
2. Wait for approval from code owner
3. Click "Rebase and merge"
4. Delete the feature branch after merging

**Result:**
```
* d4e5f6g (dev) docs: update README
* c3d4e5f (dev) test: add tests
* b2c3d4e (dev) feat: add new feature
|
* a1b2c3d (dev) Previous commit
```

---

## Branch Protection Rules

| Rule | Setting |
|------|---------|
| Target branches | `main`, `dev`, `stag` |
| Direct pushes | ❌ Blocked (bypass list only) |
| Pull requests required | ✅ Required |
| Allowed merge methods | Rebase only |
| Linear history | ✅ Enforced |
| Force pushes | ❌ Blocked (bypass list only) |
| Code owner approval | ✅ Required |

---

## Pull Request Workflow

### 1. Create PR

```bash
# Push your feature branch
git push origin feat/your-feature

# Or set upstream to push future commits
git push -u origin feat/your-feature
```

Then create PR on GitHub:
- Base: `dev`
- Compare: `feat/your-feature`

### 2. PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tested locally
- [ ] Added/updated tests
- [ ] Documentation updated

## Checklist
- [ ] Commits follow conventional commit format
- [ ] No merge commits in branch
- [ ] PR ready for review
```

### 3. Merge PR

**Note:** This repository allows **rebase merging only**.

**GitHub PR:**
1. Create PR from `feat/*` to `dev` (or `main`/`stag`)
2. Wait for approval from code owner (see [CODEOWNERS](.github/CODEOWNERS))
3. Click "Rebase and merge"
4. Delete the feature branch after merging

---

## Syncing Feature Branch

When `dev` has new changes while you're working on a feature:

```bash
# From your feature branch
git checkout feat/your-feature

# Rebase onto latest dev
git rebase dev

# If conflicts occur, resolve them:
# 1. Edit conflicted files
# 2. git add <resolved-files>
# 3. git rebase --continue

# If rebase fails, abort and try again later
git rebase --abort
```

**Why rebase?**
- Keeps your feature branch up-to-date with `dev`
- Maintains clean, linear history
- Prevents merge conflicts when creating PR

**Note:** If you're not comfortable resolving rebase conflicts, coordinate with your team before rebasing.

---

## Updating `dev` from `main`

When `main` has changes that should be in `dev` (e.g., after a hotfix):

```bash
# Fast-forward merge from main to dev
git checkout dev
git pull origin dev
git merge main --ff-only
git push origin dev
```

**If `--ff-only` fails** (branches have diverged):

**Option 1: Create a PR (Recommended for teams)**
```bash
# Create branch from main
git checkout main
git checkout -b sync/main-to-dev

# Push and create PR to dev
git push -u origin sync/main-to-dev
# On GitHub, create PR: sync/main-to-dev → dev
# Use "Rebase and merge"
```

**Option 2: Rebase dev (Only for solo maintainers or with team coordination)**
```bash
# ⚠️  WARNING: This rewrites dev history
# Coordinate with team before doing this

git checkout dev
git rebase main
git push origin dev --force-with-lease
```

---

## Hotfix to `main`

For critical fixes that need to go directly to `main`:

**Option 1: Via PR (Recommended)**
```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-fix

# Make changes and commit
git add .
git commit -m "fix: critical production issue"

# Push and create PR to main
git push -u origin hotfix/critical-fix
# Then create PR on GitHub and use "Rebase and merge"

# Also merge to dev
git checkout dev
git merge hotfix/critical-fix --ff-only
git push origin dev
```

**Option 2: Direct Push (Requires Bypass Permission)**
```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-fix

# Make changes and commit
git add .
git commit -m "fix: critical production issue"

# Fast-forward merge to main (only if in bypass list)
git checkout main
git merge hotfix/critical-fix --ff-only
git push origin main

# Also merge to dev
git checkout dev
git merge hotfix/critical-fix --ff-only
git push origin dev
```

---

## Git History Best Practices

### DO:
- ✅ Use conventional commit messages
- ✅ Keep commits atomic (one logical change per commit)
- ✅ Use `--ff-only` when possible
- ✅ Write descriptive commit messages
- ✅ Rebase feature branches before merging

### DON'T:
- ❌ Include merge commits in feature branches
- ❌ Mix unrelated changes in one commit
- ❌ Force push to shared branches (`main`, `dev`, `stag`) without team coordination

---

## Common Git Commands

```bash
# Check current branch
git branch --show-current

# See branch history
git log --oneline --graph --all

# See unpushed commits
git log origin/dev..HEAD

# See what will be merged
git log dev..feat/your-feature

# Abort a rebase
git rebase --abort

# Clean up merged branches
git branch -d feat/your-feature  # local
git push origin --delete feat/your-feature  # remote
```

---

## Summary: Recommended Workflow

1. **Create feature branch** from `dev`: `git checkout -b feat/my-feature`
2. **Make atomic commits** with conventional messages
3. **Push and create PR** to `dev`
4. **Use "Rebase and merge"** (only option available)
5. **Delete feature branch** after merge

This results in a clean, linear git history that's easy to read and debug.

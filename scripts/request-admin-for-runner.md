# Request for ArieGoldkin: Self-Hosted Runner Setup

Hey Arie! 👋

We want to set up a self-hosted GitHub Actions runner on my M4 Max Mac Studio.
This will make the repo private-ready AND give us free unlimited CI/CD.

## What You Need to Do (2 options)

### Option A: Grant me admin access (easiest, 30 seconds)

1. Go to: https://github.com/ArieGoldkin/SkillForge/settings/access
2. Find **yonatangross** in the collaborators list
3. Change role from **Write** to **Admin**
4. I'll handle the rest!

### Option B: Run these commands yourself (5 minutes)

If you prefer to keep admin access restricted, run these on your machine:

```bash
# 1. Get a runner registration token
gh api repos/ArieGoldkin/SkillForge/actions/runners/registration-token \
  --method POST --jq '.token'

# 2. Send me that token (it expires in 1 hour)
```

Then I'll set up the runner on my Mac using that token.

### Option C: Make repo private first (if you want)

```bash
# Make repo private via gh CLI
gh repo edit ArieGoldkin/SkillForge --visibility private
```

## Why This Matters

| Current | After Setup |
|---------|-------------|
| Public repo (anyone can fork) | Private repo (code hidden) |
| MIT license (anyone can sell) | BSL 1.1 (protected until 2028) |
| $0.008/min CI costs | FREE forever (my Mac) |
| Slow GitHub runners | 3-5x faster on M4 Max |

## The Code Changes (Already Done)

I've already updated:
- ✅ LICENSE → BSL 1.1
- ✅ All 17 workflows → self-hosted runner
- ✅ Setup script ready at `scripts/setup-github-runner.sh`

Just need your help with the admin stuff!

---
*Generated with Claude Code*

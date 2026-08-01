# Remote Hosting Guide

This component is source-host agnostic. The repository can be mirrored to GitHub and Gitee with two named remotes.

Recommended remote names:

```text
origin  GitHub
gitee   Gitee
```

Initial setup:

```bash
git remote add origin git@github.com:<account>/ai-coding-java.git
git remote add gitee git@gitee.com:<account>/ai-coding-java.git
```

If `origin` already points to GitHub, only add the Gitee remote:

```bash
git remote add gitee git@gitee.com:<account>/ai-coding-java.git
```

Push both remotes:

```bash
git push origin main
git push gitee main
```

Rules:

1. Keep the default branch name `main` on both hosts.
2. Use the same public-safe source content on both hosts.
3. Do not commit local Git hook files from `.git/hooks/`; they are installed per clone.
4. Do not rely on host-specific CI, issue, or release features for core template behavior.
5. Before reporting a mirror is synced, compare local `HEAD` with both remote `main` refs.

Verification:

```bash
git rev-parse HEAD
git ls-remote --heads origin main
git ls-remote --heads gitee main
```

# CLAUDE.md

Claude-specific guidance for working on this repo. See `AGENTS.md` for full developer/agent context.

## SKILL.md frontmatter gotchas

Claude Cowork's plugin validator is strict. The local `claude plugin validate` does **not** catch these — they fail silently on Cowork upload with a generic "validation error":

- **`description` is hard-capped at 1024 characters** (after YAML folding `>` / quoting). Going over by even 1 char rejects the whole plugin. When editing rename refs inside a description, recount with:
  ```bash
  python3 -c "import yaml,re; t=open('skills/X/SKILL.md').read(); m=re.match(r'---\n(.*?)\n---',t,re.S); print(len(yaml.safe_load(m.group(1))['description']))"
  ```
  Trim filler words first; cutting trigger phrases hurts invocation.
- **`argument-hint` with multiple brackets must be quoted.** `argument-hint: [env] [workflow]` is invalid YAML (two flow sequences in a row). Use `argument-hint: "[env] [workflow]"`. Single `[x]` is valid unquoted.
- **`name` should equal the folder name.** Mismatches load but feel surprising; keep them aligned.

When a Cowork upload fails opaquely, suspect description length first — `blueprint-review` hit this when `torque-api` (10 chars) → `zero-touch-api` (14 chars) in its description pushed it from 1021 → 1025.

## Rename / refactor process

Cowork caches by plugin name + version. After a failed upload:
1. Bump version in `.claude-plugin/plugin.json`.
2. Remove the stale entry from Cowork's Plugins UI before re-uploading.
3. If still silent-fails, restart Claude desktop or sign out/in.

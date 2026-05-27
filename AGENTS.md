# AGENTS.md

Orients AI coding agents (Claude Code, Cursor, Codex, Aider, etc.) working on the **zero-touch** plugin.

## What this repo is

A [Claude Code plugin](https://docs.claude.com/claude-code) for [Quali Torque](https://www.quali.com/torque/). It bundles:

- **Skills** (`skills/<name>/SKILL.md`) — domain knowledge + procedures. Claude auto-triggers them by matching the user's intent against each skill's `description`. A skill can also be invoked as a slash command (e.g. `/launch-env`) when the user types its name. No folder-prefix convention distinguishes knowledge skills from commands — Claude Code unified that in early 2026. Commands just add `argument-hint:` frontmatter.
- **Torque API integration** (`skills/zero-touch-api/`) — shared Python helper (`torque_api.py`, stdlib only) + per-endpoint example scripts + reference docs. All skills make Torque REST calls through these scripts; the helper handles auth (config file or `TORQUE_API_TOKEN`), host (config file or `TORQUE_API_HOST`, default `portal.qtorque.io`), and typed error mapping.

## Repository layout

```
.
├── .claude-plugin/
│   ├── plugin.json              # plugin manifest (name, version, author)
│   ├── marketplace.json         # marketplace entry
│   └── settings.json            # plugin-level permission allowlist
├── .github/ISSUE_TEMPLATE/      # GitHub issue templates
├── assets/icon.png              # marketplace icon (placeholder)
├── skills/                      # one folder per skill (see below)
│   ├── zero-touch-api/          # shared Torque REST helper + example scripts + references
│   └── <skill>/SKILL.md
├── pack.sh                      # build distributable zip
├── suggested-settings.json      # canonical user-settings allowlist
├── AGENTS.md / CLAUDE.md        # dev-facing docs (excluded from zip)
└── README.md                    # user-facing
```

## Conventions

### Skills

- Each skill lives in its own directory under `skills/`.
- Required file: `SKILL.md` with frontmatter `name` and `description`. `name` MUST equal the folder name.
- `description` should be rich with trigger phrases — that's how Claude decides when to invoke the skill.
- A skill becomes slash-invocable by adding `argument-hint:` frontmatter. It's still discoverable by description too.
- The body should be thin orchestration when the skill is primarily a command — defer domain knowledge to other skills via "invoke the `<skill>` skill" rather than duplicating it.
- Reference files (`references/foo.md`) are allowed and loaded on demand.
- Reference plugin files via `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/SKILL.md`.

### Torque API access

- Every Torque REST call goes through `skills/zero-touch-api/scripts/torque_api.py` (helper, stdlib only) or one of the per-endpoint example scripts in `skills/zero-touch-api/scripts/examples/`. **No skill calls `curl` or `urllib` directly.**
- Endpoint table, response shapes, and error mapping live in `skills/zero-touch-api/references/`.
- Adding a new Torque API operation = three mechanical steps (row in `endpoints.md`, new example script, reference from consuming skill). Recipe in `skills/zero-touch-api/SKILL.md`.

## When making changes

### Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with proper frontmatter (`name` matches folder).
2. Write the `description` field with many trigger phrases — invocation is description-driven.
3. If slash-invocable, add `argument-hint:` frontmatter.
4. Structure the body in clear numbered steps. Include best practices and "never do" lists where applicable.
5. **Document it in `README.md` — this is mandatory, not optional. The README is the only user-facing skill inventory; an undocumented skill is effectively invisible.**
   - Knowledge / auto-triggered skill → add a row to the **Skills** table.
   - Slash-invocable skill (has `argument-hint:` frontmatter) → add a row to the **Commands (user-invocable skills)** table, using `/skill-name [arg]`.
   - A skill can warrant both (e.g. a knowledge skill that's also `/`-callable).
6. Sanity check before committing: every dir under `skills/` should appear in README. Quick audit —
   ```bash
   for d in skills/*/; do s=$(basename "$d"); grep -q "$s" README.md || echo "MISSING from README: $s"; done
   ```

### SKILL.md frontmatter gotchas

Claude Cowork's plugin validator is strict. The local `claude plugin validate` does **not** catch these — they fail silently on Cowork upload with a generic "validation error":

- **`description` is hard-capped at 1024 characters** (after YAML folding `>` / quoting). Going over by even 1 char rejects the whole plugin. When editing rename refs inside a description, recount with:
  ```bash
  python3 -c "import yaml,re; t=open('skills/X/SKILL.md').read(); m=re.match(r'---\n(.*?)\n---',t,re.S); print(len(yaml.safe_load(m.group(1))['description']))"
  ```
  Trim filler words first; cutting trigger phrases hurts invocation.
- **`argument-hint` with multiple brackets must be quoted.** `argument-hint: [env] [workflow]` is invalid YAML (two flow sequences in a row). Use `argument-hint: "[env] [workflow]"`. Single `[x]` is valid unquoted.
- **`name` must equal the folder name.**

When a Cowork upload fails opaquely, suspect description length first — `blueprint-review` hit this when `torque-api` (10 chars) → `zero-touch-api` (14 chars) in its description pushed it from 1021 → 1025.

### Renaming a skill

1. `git mv skills/<old> skills/<new>`.
2. Update `name:` in `SKILL.md`.
3. `grep -r '<old>'` across `*.md`, `*.json`, `*.sh`, `*.py`, `*.yaml`, `*.yml` (excluding `.git/` and `dist/`) and update every hit: paths (`${CLAUDE_PLUGIN_ROOT}/skills/<old>/...`), prose mentions, slash commands, README skills table, permission glob patterns in `.claude-plugin/settings.json` + `suggested-settings.json`.
4. If the new name is longer, **re-check description lengths** for the renamed skill AND any skill whose description mentions it.
5. Bump `version` in `.claude-plugin/plugin.json`, run `./pack.sh`, validate, upload.

### Avoid

- **Never** commit a `TORQUE_API_TOKEN` value to any file.
- **Don't** make raw HTTP calls (`curl`, `urllib`, `requests`) from skills. Use `skills/zero-touch-api/scripts/` so auth, host, and error semantics stay centralized. If the endpoint isn't wrapped yet, add a small example script there first.
- **Don't** add `.DS_Store`, IDE files, or local caches — `.gitignore` excludes them; keep it that way.

## Testing

Manual: build with `./pack.sh`, install via Claude Code CLI or upload to Claude Cowork, then trigger each skill via natural-language prompts and run every slash command. No automated test suite yet.

## License

License pending — see `README.md`. Don't add code from incompatibly-licensed sources until the license decision is made.

## Roadmap

See `PLAN.md` for the remaining work (governance files, CI, marketplace prep, release).

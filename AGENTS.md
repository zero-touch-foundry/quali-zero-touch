# AGENTS.md

This file orients AI coding agents (Claude Code, Cursor, Codex, Aider, etc.) working on the **quali-claude-plugin** repository.

## What this repo is

A [Claude Code plugin](https://docs.claude.com/claude-code) for [Quali Torque](https://www.quali.com/torque/). It bundles:

- **Knowledge skills** (`skills/torque-*`, `skills/aws-*`, `skills/k8s-*`) — auto-triggered by Claude based on the user's intent, matched against each skill's `description`.
- **User-invocable skills** (`skills/command-*`) — slash-invocable (e.g. `/launch-env`). Same SKILL.md format as knowledge skills; the prefix is a convention, not a runtime requirement. (As of early 2026 Claude Code unified `commands/` into the skills system.)
- **Torque API integration** (`skills/torque-api/`) — shared Python helper (`torque_api.py`, stdlib only) + per-endpoint example scripts + reference docs. All other skills make Torque REST calls through these scripts; the helper handles auth (`TORQUE_API_TOKEN`), host (`TORQUE_API_HOST`, default `portal.qtorque.io`), and typed error mapping.

## Repository layout

```
.
├── .claude-plugin/plugin.json   # plugin manifest (name, version, author)
├── .github/ISSUE_TEMPLATE/      # GitHub issue templates
├── assets/icon.png              # marketplace icon (placeholder)
└── skills/                      # unified skills directory
    ├── torque-api/              # shared Torque REST helper + example scripts + references
    ├── command-*/SKILL.md       # user-invocable (slash) skills
    └── <other>/SKILL.md         # auto-triggered knowledge skills
```

## Conventions

### Skills

- Each skill lives in its own directory under `skills/`.
- Required file: `SKILL.md` with frontmatter `name` and `description`.
- `description` should be rich with trigger phrases — that's how Claude decides when to invoke the skill.
- Skills prefixed `torque-*` mirror the public [`torque-ai-skills` repo](https://github.com/QualiTorque) and should stay in sync.  **Don't fork them here — PR upstream.**
- Generic skills (`aws-best-practices`, `k8s-operations`, `cost-analysis`) are plugin-local — edit directly.
- Reference files (`references/foo.md`) are allowed and loaded on demand.

### Commands

- User-invocable "commands" are skills under `skills/command-<name>/SKILL.md` with `name`, `description`, and `argument-hint` frontmatter. Default `user-invocable: true` is implicit; do not set it explicitly unless overriding.
- Commands should be thin orchestration layers — defer technical knowledge to skills.
- When a command needs domain knowledge (e.g., blueprint structure), it should explicitly say "invoke the X skill" rather than re-implementing the knowledge.
- Reference plugin files via `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/SKILL.md`.

### Torque API access

- Every Torque REST call goes through `skills/torque-api/scripts/torque_api.py` (helper, stdlib only) or one of the per-endpoint example scripts in `skills/torque-api/scripts/examples/`. **No skill calls `curl` or `urllib` directly.**
- Auth: helper reads `TORQUE_API_TOKEN` from env. Host: `TORQUE_API_HOST` (default `portal.qtorque.io`). Never commit a token.
- Endpoint table, response shapes, and error mapping live in `skills/torque-api/references/`.
- Adding a new Torque API operation = three mechanical steps (row in `endpoints.md`, new example script, reference from consuming skill). Recipe in `skills/torque-api/SKILL.md`.

## When making changes

### Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with proper frontmatter.
2. Write the `description` field with many trigger phrases — invocation is description-driven.
3. Structure the body in clear numbered steps. Include best practices and "never do" lists where applicable.
4. Add a row to the README's Skills table.
5. If the skill should also live in the upstream `torque-ai-skills` repo, plan that PR too.

### Adding a new command

1. Create `skills/command-<name>/SKILL.md` with `name`, `description`, and `argument-hint` frontmatter.
2. Use `@$1`, `$ARGUMENTS` syntax for arguments — unchanged from the old commands format.
3. Add a row to the README's Commands table.

### Changing skill names

- Search the entire repo for the old name — commands reference skills by path (`${CLAUDE_PLUGIN_ROOT}/skills/<name>`).
- Update the README's Skills table.

### Avoid

- **Never** commit a `TORQUE_API_TOKEN` value to any file.
- **Don't** copy generic LLM advice into a `torque-*` skill — those skills are about Torque specifics. Generic guidance belongs in `aws-best-practices` / `k8s-operations` / a new generic skill.
- **Don't** make raw HTTP calls (`curl`, `urllib`, `requests`) from skills. Use `skills/torque-api/scripts/` so auth, host, and error semantics stay centralized. If the endpoint isn't wrapped yet, add a small example script there first.
- **Don't** add `.DS_Store`, IDE files, or local caches — `.gitignore` excludes them; keep it that way.

## Testing

Manual: install the plugin locally with `claude plugin install ./`, then trigger each skill via natural-language prompts and run every `/command`. There is no automated test suite yet — adding one is on the roadmap (see `PLAN.md`).

## License

License pending — see `README.md`. Don't add code from incompatibly-licensed sources until the license decision is made.

## Roadmap

See `PLAN.md` for the remaining work (governance files, CI, marketplace prep, release).

# Host compatibility

Facts below were checked against official documentation on 2026-10-16. Host behavior changes between versions; re-check the linked pages when a host is upgraded. The skill core (SKILL.md, references, scripts) is identical for every host; only the install location, invocation prefix, and reminder mechanism differ.

## Skill locations

| Host | User scope | Project scope | Notes |
| --- | --- | --- | --- |
| Codex CLI / IDE | `~/.agents/skills/rapih-in/` | `<repo>/.agents/skills/rapih-in/` (scanned from cwd up to repo root) | Also `/etc/codex/skills` (admin). Duplicate names are not merged; both may appear. |
| Claude Code | `~/.claude/skills/rapih-in/` | `<repo>/.claude/skills/rapih-in/` | Precedence: enterprise > personal > project. Live reload of existing skill dirs; new top-level dir needs `/reload-skills`. |
| Antigravity App | `~/.gemini/config/skills/rapih-in/` | `<repo>/.agents/skills/rapih-in/` | Legacy workspace `.agent/skills` still read. |
| Antigravity IDE | `~/.gemini/config/skills/rapih-in/` (legacy `~/.gemini/antigravity/skills/` also read) | `<repo>/.agents/skills/rapih-in/` | Active skills visible under the agent panel Customizations menu. |
| Antigravity CLI | `~/.gemini/antigravity-cli/skills/rapih-in/` | `<repo>/.agents/skills/rapih-in/` | Different global path from App/IDE. |
| Cursor Agent | `~/.agents/skills/rapih-in/` or `~/.cursor/skills/rapih-in/` | `<repo>/.agents/skills/` or `<repo>/.cursor/skills/` | Also reads `~/.claude/skills`, `~/.codex/skills`, `.claude/skills`, `.codex/skills` for compatibility; `name` must equal the folder name. |
| Kimi Code CLI | `~/.agents/skills/rapih-in/` or `$KIMI_CODE_HOME/skills/rapih-in/` (default `~/.kimi-code/skills/`) | `<repo>/.agents/skills/` or `<repo>/.kimi-code/skills/` | Precedence: project > user > extra > built-in. Older Kimi CLI docs mention `.kimi`; match the installed version. |

`~` is the home directory of the user running the agent. On Windows that is `%USERPROFILE%` (for example `C:\Users\<name>`); inside WSL it is the Linux home, which is a different filesystem with its own installs and its own `~/.rapih-in` state.

**Duplicate discovery**: Cursor reads both `~/.agents/skills` and `~/.claude/skills`, so with both installs present it sees two `rapih-in` copies. The install tool keeps them byte-identical (`verify` compares hashes), so the effective content is the same; do not create further copies (for example `~/.cursor/skills`) unless a host needs them.

## Invocation

All of these are chat input to the agent, not terminal commands.

| Host | Explicit | Automatic |
| --- | --- | --- |
| Codex CLI / IDE | `$rapih-in all --dry-run` (or pick from `/skills`) | Yes, by description (`policy.allow_implicit_invocation`, default true) |
| Claude Code | `/rapih-in all --dry-run` (arguments arrive as `ARGUMENTS: ...`) | Yes unless `disable-model-invocation: true` (not set) |
| Cursor Agent | `/rapih-in all --dry-run` | Yes unless `disable-model-invocation: true` (not set) |
| Kimi Code CLI | `/skill:rapih-in all --dry-run` | Yes unless `disableModelInvocation` or `type: flow` (neither set) |
| Antigravity App | `/rapih-in all --dry-run` | Yes |
| Antigravity CLI | `/rapih-in all --dry-run` (skills become slash commands) | Yes |
| Antigravity IDE | No documented slash command for skills; write "Use the rapih-in skill in all mode with --dry-run on this project." | Yes |

**Shortcut commands.** Next to `rapih-in/`, the installer places seven thin skills `rapih-in-audit`, `rapih-in-plan`, `rapih-in-fix`, `rapih-in-check`, `rapih-in-place`, `rapih-in-all`, `rapih-in-resume`, so hosts list one command per mode (`/rapih-in-audit`, `$rapih-in-audit`, `/skill:rapih-in-audit`). They only load `../rapih-in/SKILL.md` and run that mode. They are manual-only: `disable-model-invocation: true` (Claude Code, Cursor, Kimi) and `policy.allow_implicit_invocation: false` in `agents/openai.yaml` (Codex). Antigravity documents no manual-only flag, so there the shortcuts rely on their description ("run only when invoked explicitly"). `argument-hint` is a Claude Code field; other hosts ignore unknown fields per their docs or were not verified. Install without them: `python tools/sync.py install --no-shortcuts`.

Automatic matching is a model decision, not a guarantee that the skill runs on every action. Distinguish installed (files present), detected (host lists it), and invoked (host loaded it for this turn).

## Reminders (persistent instructions)

| Host | User scope | Project scope |
| --- | --- | --- |
| Codex | `AGENTS.md` in the Codex home (`$CODEX_HOME`, default `~/.codex/AGENTS.md`); `AGENTS.override.md` there takes precedence if non-empty | `AGENTS.md` per directory, root to cwd; 32 KiB default combined limit |
| Claude Code | `~/.claude/rules/*.md` (no `paths` frontmatter = always loaded) or `~/.claude/CLAUDE.md` | `CLAUDE.md` / `.claude/rules/`; reads `AGENTS.md` when no `CLAUDE.md` exists (v2.1.277+), or import it with `@AGENTS.md` |
| Antigravity App / IDE | `~/.gemini/GEMINI.md`, `~/.gemini/AGENTS.md`, or `~/.gemini/config/rules/*.md` with `trigger: always_on` frontmatter | `AGENTS.md`/`GEMINI.md`, or `.agents/rules/*.md` with `trigger` frontmatter |
| Antigravity CLI | as above plus `~/.gemini/antigravity-cli/rules/*.md` | as above |
| Cursor Agent | User Rules in Customize -> Rules (UI setting, no documented file) | `AGENTS.md`, or `.cursor/rules/*.mdc` with `alwaysApply: true` (plain `.md` there is ignored) |
| Kimi Code CLI | `$KIMI_CODE_HOME/AGENTS.md` (default `~/.kimi-code/AGENTS.md`) or `~/.agents/AGENTS.md` | `AGENTS.md` or `.kimi-code/AGENTS.md` |

Rule frontmatter is host-specific: never put Cursor `.mdc` frontmatter in Antigravity rules or the reverse. Cursor rules apply to Agent (chat), not Tab or Inline Edit. Reminders strengthen consistency; they do not replace host permissions or deterministic checks (lint, CI).

## Remote and sandboxed environments

User-scope installs exist only on the filesystem where they were written. Cloud agents, SSH remotes, dev containers, and WSL need their own install (or a project-scope install committed to the repo). Never claim the skill is available in an environment that was not checked. Do not enable cloud sync without a request.

## Sources

- https://developers.openai.com/codex/skills/ (redirects to learn.chatgpt.com/docs/build-skills)
- https://developers.openai.com/codex/guides/agents-md/
- https://code.claude.com/docs/en/skills · https://code.claude.com/docs/en/memory
- https://www.antigravity.google/docs/skills · https://www.antigravity.google/docs/rules/
- https://cursor.com/docs/skills · https://cursor.com/docs/rules
- https://moonshotai.github.io/kimi-code/en/customization/skills.html
- https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents

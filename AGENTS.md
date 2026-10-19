# AGENTS.md — V1.2

## Conversation Start

On the first user turn of a new conversation, check the [GitHub master](https://github.com/ArtrixTech/artrix-skills/blob/main/AGENTS.md) before other work. Detect updates by commit/content, even when the version label is unchanged.

- For downstream copies, compare shared rules against the last adopted upstream commit, recorded as `<!-- agents-upstream: SHA -->` in **Repo-Specific Rules**. Recover a missing baseline from history; ask before overwriting differences if the baseline is unknown.
- If only upstream changed, immediately replace the shared rules and preserve **Repo-Specific Rules**.
- If shared rules have local edits, ask how to merge, even if Git can merge cleanly. Propose adopting upstream and appending the private changes as local overrides in **Repo-Specific Rules**; wait for the user's choice.
- After any accepted update, record the adopted upstream SHA, reread this file, and immediately commit only `AGENTS.md` in a dedicated commit. Leave unrelated changes untouched; sync commits are exempt from devlog.

If GitHub is unavailable, retain the local file and report the check as unavailable.

## 1. Problem and Judgment

- **Goal-driven:** Define success and keep the original goal in view across long tasks and handoffs.
- **First principles:** Verify the problem and technical assumptions against current primary evidence. For faults, seek root causes.
- **Critical thinking:** Distinguish fact from inference, question your own conclusions, and follow the evidence.
- **Uncertainty:** Investigate first. Clarify consequential ambiguity; make explicit assumptions for low-impact, reversible choices.

## 2. Design and Changes

- **Occam's razor:** Choose the simplest solution that meets real requirements. Avoid speculative complexity.
- **Surgical changes:** Keep edits within scope, match existing style, and clean up only what your changes make obsolete.
- **High cohesion, low coupling:** Give components clear responsibilities and interfaces. Align logical components, implementation boundaries, and file locations.
- **Place before create:** Establish ownership before adding files or directories.
- **Dependency direction:** Keep source dependencies acyclic; runtime communication may be bidirectional.

### Architecture.md

Each project maintains an `Architecture.md` at root — a living map of the current structure, not a design document.

Format:
```markdown
# Architecture

## Components
<list of logical components, each with a one-sentence description and its file-level location>

## Key Relationships (optional)
<brief prose on dependency/containment/data-flow between components, only when the component list alone is ambiguous>
```

Rules:
- Update when structure changes (component added/removed/split/merged, directory moved). Not for implementation-detail changes.
- Each entry connects the logical role to its physical location — don't describe one without the other.
- Keep it factual (what *is*), not aspirational (what *should be*).

## 3. Execution and Verification

- Sequence dependencies; batch independent work. Delegate when parallel work warrants it.
- Match verification to the claim and the risk. For fixes, establish a baseline and compare before and after.
- **Adversarial review:** For substantial changes or important decisions, have an uninvolved agent seek counterexamples and provide evidence.
- **Independent judgment:** In multi-agent assessments, form conclusions independently before comparing them. Consensus is not proof.
- **Ablation:** Use controlled removal to evaluate a factor's contribution when that contribution matters to the decision.

Routine lookup and trivial edits do not require adversarial review or ablation.

## 4. Delivery and Recalibration

- Report what was achieved, what supports it, and what remains materially uncertain.
- Be concise. No flattery or filler; never open with "you are right".

## 5. Git & Commits

### Commit Style

- Use **Gitflow** branch naming and workflow conventions.
- Commit messages in **English**.
- Format: `<type>(<scope>): <subject>` (e.g., `feat(auth): add JWT refresh token rotation`).
- Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`, `perf`, `ci`.
- Subject line: imperative mood, no period, ≤72 chars.
- Body (optional): explain *why*, not *what*. Wrap at 72 chars.

### Commit Discipline

- Make atomic commits after each conversation turn that produces changes.
- Unless the user explicitly requests otherwise, commit on the current branch — do not create sub-branches.
- Each commit should be self-contained and the repo should remain in a buildable/runnable state after every commit.

## 6. Documentation

### devlog.md (`docs/devlog.md`)

A running development log organized in reverse-chronological blocks.

Each block represents one commit:

```markdown
## <commit title>

`<commit hash>` | <date>

- **Changes**: <what was modified, compressed>
- **Reason**: <why>
- **User feedback**: <original user request/feedback, if any>
- **Process**: <experiments, tests, iterations — if any>
- **Result**: <outcome, effect, status>
- **Notes**: <anything useful for future tracing/debugging>
```

Rules:
- One block per commit. Add the commit hash after committing (the devlog update rides with the next commit — no dedicated commit needed).
- Keep text compressed but information-complete.
- Record anything that might aid future tracing or debugging.

### Precipitation Docs (`docs/precipitation/<YYMMDD>_<brief_name>.md`)

Long-lived knowledge artifacts: reflections, lessons learned, pitfalls, reusable workflows (debugging, migration, etc.), methodology.

Decision criterion: write a precipitation doc when the content is **durable and transferable** — valuable beyond the immediate task.

File format:
```markdown
# <Title>

## Summary
<1-3 sentence overview of what this document covers and why it exists>

## Content
<detailed content>
```

Naming rules:
- `YYMMDD` date prefix for chronological sorting.
- `brief_name` uses accurate keywords for future recall (e.g., `250713_playwright_flaky_test_strategy.md`).

---

## 7. Repo-Specific Rules

<!-- agents-upstream: 78c3a9472c5ab08b471f531746c99c8ad82f9caa -->

Local additions and overrides belong here and take precedence over shared defaults. Preserve this section when syncing; do not import the upstream repository's private rules.

### elec-price-hunter

- 与用户交流使用简体中文；commit message、代码与 SKILL.md 保持英文。
- 脚本只用 Python 3 标准库，不引入第三方依赖。
- 改动任何渠道适配器后，须跑 `python3 -m unittest discover -s tests` 与 `python3 skills/elec-price-hunter/scripts/eph.py check`，结果记入 devlog。
- 上游接口返回结构变化时报 `SchemaError`，不静默返回空值或零价。

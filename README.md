# sql-dojo

Personal SQL and data modeling practice, coached by Claude Code, on a DTC wine world in DuckDB.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 seed/seed_wine_world.py        # builds wine.duckdb
```

Optional: install the DuckDB CLI (`brew install duckdb`) to explore the data from the terminal, or run `duckdb -ui wine.duckdb` for a browser notebook.

Then run `claude` in this folder. On the first session Claude creates `progress/profile.md` from the template and asks about your background and goal.

## Loop

1. `claude` in this folder, then ask for a problem
2. Write `solutions/<pid>.sql`, and preview it with `duckdb -readonly wine.duckdb -f solutions/<pid>.sql`
3. `python3 grader/grade.py <pid> solutions/<pid>.sql`
4. Review with Claude, then "log it"

## Layout

- `seed/` builds the base world (deterministic)
- `problems/<pid>/` problem.md, setup.sql (trap data), `.answer/` (reference, wrong answers, hints)
- `grader/grade.py` runs your query and the reference against the base data plus trap rows, then diffs the results (trap rows are rolled back after each run)
- `progress/` profile.md (Claude updates, created from profile.template.md) and attempts.jsonl (grader writes)
- `scripts/export_template.sh` copies the shareable files into the template repo

## Sharing (maintainers)

This repo holds personal progress. The public template repo gets only the engine and problems:

```bash
scripts/export_template.sh ../sql-dojo-template   # a checkout of the template repo
cd ../sql-dojo-template && git add -A && git commit -m "Sync problems" && git push
```

The script skips `progress/profile.md`, `progress/attempts.jsonl` and `solutions/*.sql`, and fails if any exported file mentions the learner's name.

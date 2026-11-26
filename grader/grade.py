#!/usr/bin/env python3
"""
Grade a SQL solution against the reference answer.

Usage:
    python grader/grade.py <pid> <solution.sql>   # grade a solution
    python grader/grade.py <pid> --validate        # check that wrong_*.sql files all fail
"""
import sys, os, json, duckdb
from datetime import datetime, timezone
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DB_PATH  = ROOT / "wine.duckdb"
PROGRESS = ROOT / "progress"


# ── result comparison ──────────────────────────────────────────────────────

def normalize(val):
    if isinstance(val, float):
        return round(val, 4)
    return val

def rows_equal(a, b):
    return tuple(normalize(x) for x in a) == tuple(normalize(x) for x in b)

def compare(exp_rows, exp_cols, act_rows, act_cols, ordered=False):
    exp_cols = [c.lower() for c in exp_cols]
    act_cols = [c.lower() for c in act_cols]

    if set(exp_cols) != set(act_cols):
        return False, (
            f"Column mismatch.\n"
            f"  Expected : {exp_cols}\n"
            f"  Got      : {act_cols}"
        )

    # Reorder actual columns to match expected
    if exp_cols != act_cols:
        idx      = {c: i for i, c in enumerate(act_cols)}
        act_rows = [tuple(r[idx[c]] for c in exp_cols) for r in act_rows]

    exp_n = [tuple(normalize(v) for v in r) for r in exp_rows]
    act_n = [tuple(normalize(v) for v in r) for r in act_rows]

    if not ordered:
        key    = lambda r: [str(x) for x in r]
        exp_n  = sorted(exp_n, key=key)
        act_n  = sorted(act_n, key=key)

    if exp_n == act_n:
        return True, None

    exp_set  = {str(r) for r in exp_n}
    act_set  = {str(r) for r in act_n}
    missing  = [r for r in exp_n if str(r) not in act_set]
    extra    = [r for r in act_n if str(r) not in exp_set]

    lines = [f"Row count: expected {len(exp_n)}, got {len(act_n)}"]
    if missing:
        lines.append(f"\nMissing from your result ({len(missing)} row(s)):")
        for r in missing[:5]:
            lines.append(f"  {r}")
        if len(missing) > 5:
            lines.append(f"  ... and {len(missing)-5} more")
    if extra:
        lines.append(f"\nExtra in your result ({len(extra)} row(s)):")
        for r in extra[:5]:
            lines.append(f"  {r}")
        if len(extra) > 5:
            lines.append(f"  ... and {len(extra)-5} more")

    return False, "\n".join(lines)


# ── database helpers ───────────────────────────────────────────────────────

def run_in_tx(setup_sql: str, query_sql: str):
    """Open wine.duckdb, run setup inside a transaction, execute query, rollback."""
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute("BEGIN")
        if setup_sql:
            con.execute(setup_sql)
        rel  = con.execute(query_sql)
        cols = [d[0] for d in rel.description]
        rows = rel.fetchall()
        return rows, cols
    finally:
        con.execute("ROLLBACK")
        con.close()


def load(path: Path) -> str:
    return path.read_text().strip()


# ── grading ────────────────────────────────────────────────────────────────

def grade(pid: str, solution_path: Path):
    prob_dir  = ROOT / "problems" / pid
    setup_sql = load(prob_dir / "setup.sql") if (prob_dir / "setup.sql").exists() else ""
    ref_sql   = load(prob_dir / ".answer" / "reference.sql")
    sol_sql   = load(solution_path)

    # Read problem title for display
    prob_md   = prob_dir / "problem.md"
    title     = prob_md.read_text().split("\n")[0].lstrip("# ").strip() if prob_md.exists() else pid

    print(f"\nProblem {pid}: {title}\n")

    exp_rows, exp_cols = run_in_tx(setup_sql, ref_sql)
    act_rows, act_cols = run_in_tx(setup_sql, sol_sql)

    # Check for ordered requirement in problem.md
    ordered = prob_md.exists() and "ordered: true" in prob_md.read_text().lower()

    passed, diff = compare(exp_rows, exp_cols, act_rows, act_cols, ordered=ordered)

    if passed:
        print(f"  PASS — {len(exp_rows)} row(s) matched")
    else:
        print(f"  FAIL\n\n{diff}\n")
        print(f"  Expected columns : {[c.lower() for c in exp_cols]}")
        print(f"  Expected rows    :")
        for r in exp_rows[:10]:
            print(f"    {r}")

    # Append to attempts log
    PROGRESS.mkdir(exist_ok=True)
    record = {
        "pid"      : pid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed"   : passed,
        "rows"     : len(act_rows),
    }
    with open(PROGRESS / "attempts.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")

    return passed


# ── validation (problem author mode) ──────────────────────────────────────

def validate(pid: str):
    prob_dir  = ROOT / "problems" / pid
    setup_sql = load(prob_dir / "setup.sql") if (prob_dir / "setup.sql").exists() else ""
    ref_sql   = load(prob_dir / ".answer" / "reference.sql")

    print(f"\nValidating {pid}...")

    # Reference must succeed
    exp_rows, exp_cols = run_in_tx(setup_sql, ref_sql)
    n = len(exp_rows)
    if n < 3 or n > 20:
        print(f"  WARN  reference.sql returned {n} rows (target 3–20)")
    else:
        print(f"  OK    reference.sql → {n} rows")

    # Every wrong_*.sql must produce a different result
    wrong_files = sorted((prob_dir / ".answer").glob("wrong_*.sql"))
    if not wrong_files:
        print("  WARN  no wrong_*.sql files found")

    all_ok = True
    for wf in wrong_files:
        wrong_sql  = load(wf)
        wrng_rows, wrng_cols = run_in_tx(setup_sql, wrong_sql)
        passed, _  = compare(exp_rows, exp_cols, wrng_rows, wrng_cols)
        status     = "OK   " if not passed else "FAIL "
        note       = "correctly differs" if not passed else "MATCHES reference — add more trap data"
        print(f"  {status} {wf.name} → {note}")
        if passed:
            all_ok = False

    if all_ok:
        print("\n  All checks passed.")
    else:
        print("\n  Some wrong answers match the reference — tighten the trap data.")
    return all_ok


# ── entry point ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    pid = sys.argv[1]
    if not (ROOT / "problems" / pid).is_dir():
        print(f"Problem directory not found: problems/{pid}")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"wine.duckdb not found — run: python seed/seed_wine_world.py")
        sys.exit(1)

    if sys.argv[2] == "--validate":
        ok = validate(pid)
        sys.exit(0 if ok else 1)
    else:
        solution = Path(sys.argv[2])
        if not solution.exists():
            print(f"Solution file not found: {solution}")
            sys.exit(1)
        passed = grade(pid, solution)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

"""
Gurobi-based optimal reference comparison -- deferred, optional, last.

Per the project's Gurobi policy (see thesis_docs/chapters/00_lab_log.md,
2026-08-12 entry, and CLAUDE.md rule 6): the academic license has not been
approved yet, so NOTHING in the thesis pipeline may depend on it. This
script is the single, isolated entry point for the eventual optimal-
reference run. It is:

  - self-contained: no other module in this repo imports from here;
  - safe to run at any time: it performs a license capability check on
    startup and exits cleanly (exit code 0) with an explanatory message if
    Gurobi is unavailable, rather than crashing;
  - NOT run as part of any other script, backfill, or CI step.

Until a license is available AND the actual optimal-reference model is
built (planned home: ev2gym/baselines/mpc/ or a new gurobi_models/ module,
per CLAUDE.md's Useful Commands section -- not yet written), running this
script will always report "not available" or "not yet implemented" and
exit 0. That is expected, not a bug.
"""
import sys


def check_gurobi_license() -> tuple:
    """Returns (available: bool, message: str). Never raises."""
    try:
        import gurobipy as gp
    except ImportError:
        return False, "gurobipy is not installed in this environment."

    try:
        env = gp.Env(empty=True)
        env.start()
        env.dispose()
        return True, "Gurobi license check succeeded (able to start an environment)."
    except gp.GurobiError as e:
        return False, f"gurobipy is installed but the license check failed: {e}"
    except Exception as e:
        return False, f"gurobipy is installed but an unexpected error occurred during the license check: {e}"


if __name__ == "__main__":
    available, message = check_gurobi_license()
    print(f"Gurobi available: {available}")
    print(message)

    if not available:
        print("\nExiting cleanly -- no results depend on this. The thesis reports "
              "the best-performing tested strategy and carries the optimality gap "
              "as declared future work (see thesis_docs/chapters/02_model_validation.md).")
        sys.exit(0)

    print("\nGurobi license is available, but the optimal-reference model itself "
          "has not been implemented in this codebase yet (planned for "
          "ev2gym/baselines/mpc/ or a new gurobi_models/ module). "
          "Nothing to run yet -- this is not an error.")
    sys.exit(0)

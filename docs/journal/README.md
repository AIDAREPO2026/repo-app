# Task journal

The journal is the single home for task status. Each task that has started has one file here, named after its code, for example `P1-UI-02.md`. It holds the task's status, owner, branch and pull request, a dated log, the decisions made along the way, and any blockers.

The shared planning tracker is a summary for ITPED, refreshed from this folder. If the two disagree, this folder is right.

## Rules

1. **Starting a task:** copy `_template.md` to `<CODE>.md`, fill in the table and set Status to `In progress`. Commit it as the first commit on the task branch.
2. **While working:** add a log line for each working session, newest first. Record every decision or deviation from the spec in the same pull request as the code it affects.
3. **Opening the pull request:** set Status to `In review` and add the pull request link.
4. **Blocked:** set Status to `Blocked` and fill in Blockers: what, who can unblock it, since when.
5. **Merging:** set Status to `Done` and fill in Finished, in the pull request itself, so the merge and the status land together.
6. **Coming back to a task later:** any later change that belongs to a task (a review fix, a bug fix, a follow-up, a refactor of its code, a defect `DEF-###` raised against it) updates that task's journal file in the same pull request. Add a log line saying what changed and why, record any new decision or deviation, and add the pull request to the log entry. If the task was `Done` and the change reopens its acceptance criteria, set Status back to `In progress` until the fix merges. A change that touches several tasks updates each of their journal files.
7. **No silent changes:** if the code of a task changes and its journal does not, the journal is wrong. CI refuses a pull request when the task code in its branch name, or at the start of any commit subject, has no change to that task's journal file (`P0-OPS-03`).
8. **Tracker:** after any status change above, update the task's row and the phase totals in the shared planning tracker, so ITPED never sees stale numbers. See [conventions](../conventions.md#task-journal).

Status is one of: `Not started`, `In progress`, `In review`, `Blocked`, `Done`. A task with no journal file counts as `Not started`.

One file per task means five developers never edit the same file, so journal changes never conflict.

## Checking

`scripts/build_task_index.py` reads the Status and Owner of every journal file into [the task index](../tasks/README.md). Its `--check` mode fails when a journal file names a task that does not exist, or uses a status outside the list above.

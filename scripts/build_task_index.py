"""Build docs/tasks/README.md from the phase files and the task journal, and check them.

The phase files hold each task's spec. docs/journal/<CODE>.md holds its live
status and owner; a task with no journal file is "Not started".

Run after changing any phase file or journal file:

    uv run python scripts/build_task_index.py

Use --check in CI to fail without writing when the index is stale, a task
reference points to a code that does not exist, a phase header's totals do
not match its tasks, or a journal file has an unknown code or status.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
TASKS_DIR = DOCS / "tasks"
INDEX = TASKS_DIR / "README.md"
JOURNAL_DIR = DOCS / "journal"

STATUSES = ["Not started", "In progress", "In review", "Blocked", "Done"]

PHASE_NAMES = {
    "0": "Mobilise",
    "1": "Platform and access",
    "2": "Content and governance",
    "3": "Discovery and directories",
    "4": "Hardening and release",
    "5": "Complete the SRS features",
    "6": "Independent assurance",
    "7": "Pilot, handover and launch",
}
MVP_PHASES = "01234"

TASK_HEADING = re.compile(r"^### (P\d-[A-Z0-9]+-\d+) — (.+)$")
TASK_ROW = re.compile(r"^\| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$")
TASK_CODE = re.compile(r"`(P\d-[A-Z0-9]+-\d+)`")
JOURNAL_FIELD = re.compile(r"^\| (Status|Owner) \| (.*) \|$", re.MULTILINE)


@dataclass
class Task:
    code: str
    title: str
    points: int
    role: str
    depends_on: str
    file_name: str
    status: str = "Not started"
    owner: str = ""

    @property
    def phase(self) -> str:
        return self.code[1]

    @property
    def is_qa(self) -> bool:
        return self.role == "QA"


def read_tasks() -> list[Task]:
    """Read every task from the phase files, in file order."""
    tasks: list[Task] = []
    for path in sorted(TASKS_DIR.glob("phase-*.md")):
        lines = path.read_text().splitlines()
        for number, line in enumerate(lines):
            heading = TASK_HEADING.match(line)
            if not heading:
                continue
            # The task table's data row sits four lines below the heading.
            row = TASK_ROW.match(lines[number + 4])
            if not row:
                raise SystemExit(f"{path.name}: {heading.group(1)} has no task table row")
            tasks.append(
                Task(
                    code=heading.group(1),
                    title=heading.group(2),
                    points=int(row.group(1)),
                    role=row.group(2).strip(),
                    depends_on=row.group(3).strip(),
                    file_name=path.name,
                )
            )
    return tasks


def journal_files() -> list[Path]:
    """Return every task journal file, skipping the README and the template."""
    return sorted(JOURNAL_DIR.glob("P*.md"))


def apply_journals(tasks: list[Task]) -> list[str]:
    """Copy Status and Owner from each journal file onto its task, returning any problems."""
    by_code = {task.code: task for task in tasks}
    problems: list[str] = []
    for path in journal_files():
        task = by_code.get(path.stem)
        if task is None:
            problems.append(f"journal/{path.name}: no task has the code {path.stem}")
            continue
        fields = dict(JOURNAL_FIELD.findall(path.read_text()))
        status = fields.get("Status", "").strip()
        if status not in STATUSES:
            problems.append(f"journal/{path.name}: status {status!r} is not one of {', '.join(STATUSES)}")
            continue
        task.status = status
        task.owner = fields.get("Owner", "").strip()
    return problems


def find_problems(tasks: list[Task]) -> list[str]:
    """Return every duplicate code, unknown reference and wrong phase header."""
    problems: list[str] = []
    codes = [task.code for task in tasks]
    for code in sorted({code for code in codes if codes.count(code) > 1}):
        problems.append(f"duplicate task code {code}")

    known = set(codes)
    for path in DOCS.rglob("*.md"):
        if path in (INDEX, JOURNAL_DIR / "_template.md"):
            continue
        for code in sorted(set(TASK_CODE.findall(path.read_text()))):
            if code not in known:
                problems.append(f"{path.relative_to(DOCS)}: unknown task code {code}")

    for path in sorted(TASKS_DIR.glob("phase-*.md")):
        expected = phase_header(tasks, path.name[6])
        if expected not in path.read_text():
            problems.append(f"{path.name}: header should say {expected}")
    return problems


def phase_header(tasks: list[Task], phase: str) -> str:
    """Return the totals line a phase file's header must contain."""
    count, dev, qa = totals([task for task in tasks if task.phase == phase])
    return f"**Tasks:** {count} · **Points:** {dev + qa} (Dev {dev}, QA {qa})"


def done_points(tasks: list[Task]) -> int:
    """Return the points of tasks whose journal says Done."""
    return sum(task.points for task in tasks if task.status == "Done")


def totals(tasks: list[Task]) -> tuple[int, int, int]:
    """Return task count, Dev points and QA points."""
    dev = sum(task.points for task in tasks if not task.is_qa)
    qa = sum(task.points for task in tasks if task.is_qa)
    return len(tasks), dev, qa


def anchor(task: Task) -> str:
    """Return the GitHub heading anchor for a task's spec."""
    heading = f"{task.code} — {task.title}".lower()
    return re.sub(r"[^a-z0-9 -]", "", heading).replace(" ", "-")


def render_index(tasks: list[Task]) -> str:
    """Render the full task index as Markdown."""
    mvp = [task for task in tasks if task.phase in MVP_PHASES]
    later = [task for task in tasks if task.phase not in MVP_PHASES]
    mvp_count, mvp_dev, mvp_qa = totals(mvp)
    later_count, later_dev, later_qa = totals(later)

    lines = [
        "# Task index",
        "",
        f"All {len(tasks)} tasks. The MVP (Phases 0 to 4) has {mvp_count} tasks and "
        f"{mvp_dev + mvp_qa} points. Phases 5 to 7 have {later_count} tasks and "
        f"{later_dev + later_qa} points.",
        "",
        "Each code links to its full spec. Status and owner come from each task's file in "
        "[the task journal](../journal/README.md), the single home for task status. "
        "This file is generated by `scripts/build_task_index.py`, so change the phase file "
        "or the journal and regenerate rather than editing it by hand.",
        "",
        "| Phase | Tasks | Dev points | QA points | Total | Done |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for phase, name in PHASE_NAMES.items():
        phase_tasks = [task for task in tasks if task.phase == phase]
        count, dev, qa = totals(phase_tasks)
        done = done_points(phase_tasks)
        lines.append(f"| {phase} {name} | {count} | {dev} | {qa} | {dev + qa} | {done} |")

    for phase, name in PHASE_NAMES.items():
        lines += [
            "",
            f"## Phase {phase}: {name}",
            "",
            "| Code | Task | Role | Points | Status | Owner | Depends on |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for task in tasks:
            if task.phase != phase:
                continue
            link = f"[`{task.code}`]({task.file_name}#{anchor(task)})"
            lines.append(
                f"| {link} | {task.title} | {task.role} | {task.points} | {task.status} "
                f"| {task.owner} | {task.depends_on} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    check_only = "--check" in sys.argv
    tasks = read_tasks()
    problems = apply_journals(tasks) + find_problems(tasks)
    index = render_index(tasks)

    if check_only and INDEX.read_text() != index:
        problems.append("docs/tasks/README.md is stale: run scripts/build_task_index.py")
    for problem in problems:
        print(problem)
    if problems:
        return 1

    if not check_only:
        INDEX.write_text(index)
    print(f"{len(tasks)} tasks, no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())

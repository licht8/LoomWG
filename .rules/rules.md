# LoomWG Project Rules

## For All Agents

1. **Never delete anything!** Files to be "deleted" go to `_Trash/` with a date prefix: `_Trash/2026-09-04_filename.old`.
2. **All TZs and reports** go into `.tasks/XXX_task_name/`.
3. **Before starting work** — read this file.
4. **After any change** — run `pytest` and ensure all tests pass.
5. **Commit changes** after every completed step (`git add` + `commit`).
6. **Never do more than 3 sub-tasks at once.** If a task is bigger — split it.
7. **If in doubt** — ask the coordinator (@coordinator).

## For @coordinator

1. Receive tasks from the user (Yehor).
2. Convert them into a TZ (a `.tasks/XXX/TZ.md` file).
3. Split into micro-steps (no more than 3 sub-tasks per step).
4. Assign to @executor one step at a time via Bot Chat.
5. Review results (reports in `.tasks/XXX/REPORT.md`).
6. If everything is OK — reply "ACCEPTED" and close the task.

## For @executor

1. Receive a concrete step from @coordinator.
2. Execute it strictly per the TZ.
3. Run `pytest` after every change.
4. Write a report to `.tasks/XXX/REPORT.md`.
5. If a task is more than 3 sub-tasks — ask: "@coordinator, split this task".
6. If stuck — ask: "@coordinator, help, I'm stuck on [what exactly]".
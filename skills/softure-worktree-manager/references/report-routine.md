# Report routine: moved

The roadmap report routine is now the **roadmap heartbeat**, a routine under `routines/` that follows the routine
standard (a fresh session on every fire, never bound to the coordinator's session, no dashboards):
[`routines/roadmap-heartbeat.md`](../../../routines/roadmap-heartbeat.md). It holds the setup-thread steps, the
routine prompt and how the coordinator deletes it at the end of the run.

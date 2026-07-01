# First-Run Doctor

## Command

```bash
ecl-trainer doctor github-action
```

## What It Checks

- Workflow file exists.
- Safe manifest exists.
- Local artifact files exist after a run.
- Workflow has read permissions.
- Workflow can post PR comments.
- The first policy is `report_only`.

## Output Shape

```json
{
  "doctor_profile": "github_action_first_run",
  "status": "action_required",
  "next_steps": ["add_metadata_manifest", "run_first_scan"]
}
```

## Buyer Value

The doctor turns first-run setup from a support conversation into a local diagnostic. Platform teams can self-serve the setup and show security reviewers which controls are already active.

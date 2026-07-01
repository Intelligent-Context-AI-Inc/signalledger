GITHUB_ACTION_SNIPPET = """\
- uses: ./.github/actions/ecl-trainer-scan
  with:
    project_namespace: default
    ledger_path: .ecl-trainer/events.jsonl
    risk_policy: report_only
"""

GITLAB_CI_SNIPPET = """\
include:
  - local: .gitlab-ci.ecl-trainer.yml
"""

AXOLOTL_PLUGIN_SNIPPET = """\
plugins:
  - ecl_trainer.integrations.axolotl.ECLAxolotlPlugin
"""

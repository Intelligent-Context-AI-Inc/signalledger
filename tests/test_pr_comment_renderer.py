from ecl_trainer.compliance.pr_comment import PullRequestCommentRenderer


def test_pr_comment_renderer_outputs_markdown():
    markdown = PullRequestCommentRenderer().render({"status": "pass", "risk_flags": []})
    assert "ECL Pre-Flight Shield" in markdown
    assert "No-payload" in markdown

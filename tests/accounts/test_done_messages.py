"""P1-UI-02: removals are warnings, other changes are successes, unknown keys say nothing."""

from app.accounts.router import DONE_MESSAGES, done_message


def test_p1_ui_02_removals_warn_and_other_changes_succeed() -> None:
    assert done_message("created", DONE_MESSAGES) == [("success", DONE_MESSAGES["created"])]
    assert done_message("deactivated", DONE_MESSAGES) == [("warning", DONE_MESSAGES["deactivated"])]
    assert done_message("<script>", DONE_MESSAGES) == []

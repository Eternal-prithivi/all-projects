"""Unit tests for signup notification routing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.trust.signup_notify import notify_new_user_signup


@patch("app.trust.signup_notify.EmailService")
def test_notify_skips_in_test_environment(mock_email_cls):
    with patch("app.trust.signup_notify.is_test_environment", return_value=True):
        notify_new_user_signup(
            username="reg_abc",
            email="reg_abc@example.com",
            source="register",
        )
    mock_email_cls.assert_not_called()


@patch("app.trust.signup_notify.EmailService")
def test_notify_skips_example_com_without_test_inbox(mock_email_cls):
    with patch("app.trust.signup_notify.is_test_environment", return_value=False), patch(
        "app.trust.signup_notify.is_test_signup_email", return_value=True
    ), patch.dict("os.environ", {}, clear=False) as env:
        env.pop("TEST_SIGNUP_NOTIFY_EMAIL", None)
        notify_new_user_signup(
            username="verify_abc",
            email="verify_abc@example.com",
            source="register",
        )
    mock_email_cls.assert_not_called()


@patch("app.trust.signup_notify.EmailService")
def test_notify_routes_example_com_to_test_inbox(mock_email_cls):
    mock_svc = MagicMock()
    mock_email_cls.return_value = mock_svc

    with patch("app.trust.signup_notify.is_test_environment", return_value=False), patch(
        "app.trust.signup_notify.is_test_signup_email", return_value=True
    ), patch.dict("os.environ", {"TEST_SIGNUP_NOTIFY_EMAIL": "investments957@gmail.com"}):
        notify_new_user_signup(
            username="verify_abc",
            email="verify_abc@example.com",
            source="register",
        )

    mock_svc.send_new_user_signup_notification.assert_called_once()
    assert (
        mock_svc.send_new_user_signup_notification.call_args.kwargs["to_email"]
        == "investments957@gmail.com"
    )


@patch("app.trust.signup_notify.EmailService")
def test_notify_sends_real_signups_to_default_inbox(mock_email_cls):
    mock_svc = MagicMock()
    mock_email_cls.return_value = mock_svc

    with patch("app.trust.signup_notify.is_test_environment", return_value=False), patch(
        "app.trust.signup_notify.is_test_signup_email", return_value=False
    ):
        notify_new_user_signup(
            username="jane",
            email="jane@gmail.com",
            source="register",
        )

    mock_svc.send_new_user_signup_notification.assert_called_once()
    assert mock_svc.send_new_user_signup_notification.call_args.kwargs["to_email"] is None

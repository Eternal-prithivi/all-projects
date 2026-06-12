"""Shared HTML + plain-text templates for Zenith transactional email."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Dict, Optional

from app.utils.config import settings

# Zenith brand (inline-safe for email clients)
GOLD = "#d4af37"
GOLD_LIGHT = "#ffe566"
GOLD_DARK = "#b8860b"
BG_PAGE = "#0c0c0f"
BG_CARD = "#141418"
TEXT_PRIMARY = "#f2f2f4"
TEXT_SECONDARY = "#a8a8b3"
TEXT_MUTED = "#6b6b76"
BORDER = "#2a2a32"
SUCCESS = "#3ecf8e"

SUBJECT_LABELS = {
    "general": "General inquiry",
    "support": "Technical support",
    "technical": "Technical support",
    "billing": "Billing question",
    "account": "Account",
    "others": "Other",
    "feature": "Feature request",
    "bug": "Bug report",
}


def frontend_base() -> str:
    return (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")


def subject_label(key: str) -> str:
    return SUBJECT_LABELS.get(key, key.replace("_", " ").title())


def short_ref(submission_id: Optional[str]) -> str:
    if not submission_id:
        return ""
    clean = submission_id.replace("-", "").upper()
    return clean[-8:] if len(clean) >= 8 else clean


def reference_code(submission: Dict) -> str:
    """Human-friendly ticket code stored on the submission and shown in email."""
    existing = submission.get("reference_code")
    if existing:
        return str(existing)
    ref = short_ref(submission.get("submission_id"))
    return f"ZN-{ref}" if ref else ""


def format_timestamp(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%B %d, %Y at %I:%M %p UTC")
    return str(value)


def _esc(value) -> str:
    return html.escape(str(value))


def zenith_email_html(
    *,
    preheader: str,
    eyebrow: str,
    title: str,
    body_html: str,
    footer_note: str = "Zenith Cloud Resource Optimization Platform",
) -> str:
    """Table-based layout with inline styles for broad email client support."""
    base = frontend_base()
    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="x-apple-disable-message-reformatting" />
  <meta name="color-scheme" content="dark light" />
  <meta name="supported-color-schemes" content="dark light" />
  <title>{_esc(title)}</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
  <style type="text/css">
    :root {{ color-scheme: dark light; supported-color-schemes: dark light; }}
    html, body {{
      margin: 0 !important;
      padding: 0 !important;
      width: 100% !important;
      height: 100% !important;
      background-color: {BG_PAGE} !important;
    }}
    .email-root, .email-root td {{
      background-color: {BG_PAGE} !important;
    }}
    .email-card {{
      background-color: {BG_CARD} !important;
    }}
    /* Gmail iOS/Android: reduce white letterboxing in light system theme */
    u + .body .email-root {{
      background-color: {BG_PAGE} !important;
    }}
    @media (prefers-color-scheme: dark) {{
      .email-root, .email-root td, body {{
        background-color: {BG_PAGE} !important;
      }}
      .email-card {{
        background-color: {BG_CARD} !important;
      }}
    }}
    @media (prefers-color-scheme: light) {{
      /* Keep Zenith dark transactional shell; prevents harsh white gutters on mobile */
      .email-root, .email-root td, body {{
        background-color: {BG_PAGE} !important;
      }}
      .email-card {{
        background-color: {BG_CARD} !important;
      }}
    }}
  </style>
</head>
<body class="body" bgcolor="{BG_PAGE}" style="margin:0;padding:0;width:100%;background-color:{BG_PAGE};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">{_esc(preheader)}</div>
  <table class="email-root" role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="{BG_PAGE}" style="width:100%;min-height:100vh;margin:0;padding:0;background-color:{BG_PAGE};">
    <tr>
      <td align="center" bgcolor="{BG_PAGE}" style="padding:32px 16px;background-color:{BG_PAGE};">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;margin:0 auto;">
          <tr>
            <td style="padding:0 0 20px;text-align:center;">
              <div style="font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{GOLD};">Zenith Cloud</div>
              <div style="font-size:22px;font-weight:800;color:{TEXT_PRIMARY};margin-top:6px;">{_esc(title)}</div>
              <div style="font-size:13px;color:{TEXT_MUTED};margin-top:6px;">{_esc(eyebrow)}</div>
            </td>
          </tr>
          <tr>
            <td class="email-card" bgcolor="{BG_CARD}" style="background-color:{BG_CARD};border:1px solid {BORDER};border-top:3px solid {GOLD};border-radius:14px;padding:28px 24px;color:{TEXT_SECONDARY};font-size:15px;line-height:1.65;">
              {body_html}
            </td>
          </tr>
          <tr>
            <td bgcolor="{BG_PAGE}" style="padding:22px 8px 32px;text-align:center;font-size:12px;line-height:1.6;color:{TEXT_MUTED};background-color:{BG_PAGE};">
              <p style="margin:0 0 8px;">{_esc(footer_note)}</p>
              <p style="margin:0;">
                <a href="{base}" style="color:{GOLD};text-decoration:none;">{base.replace('https://', '')}</a>
                &nbsp;·&nbsp;
                <a href="mailto:support@rajverse.me" style="color:{GOLD};text-decoration:none;">support@rajverse.me</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def field_row(label: str, value_html: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:14px;">
      <tr>
        <td style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{GOLD};padding-bottom:6px;">{_esc(label)}</td>
      </tr>
      <tr>
        <td style="background-color:#1a1a20;border:1px solid {BORDER};border-left:3px solid {GOLD};border-radius:8px;padding:12px 14px;color:{TEXT_PRIMARY};font-size:14px;line-height:1.55;">
          {value_html}
        </td>
      </tr>
    </table>"""


def primary_button(href: str, label: str) -> str:
    """Bulletproof CTA — solid fill; many clients ignore CSS gradients on buttons."""
    safe_href = _esc(href)
    safe_label = _esc(label)
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:24px 0 12px;">
      <tr>
        <td align="center">
          <table role="presentation" cellspacing="0" cellpadding="0">
            <tr>
              <td align="center" bgcolor="{GOLD}" style="background-color:{GOLD};border-radius:10px;border:1px solid {GOLD_DARK};mso-padding-alt:14px 28px;">
                <a href="{safe_href}" target="_blank" rel="noopener noreferrer"
                   style="display:inline-block;padding:14px 28px;color:#111111;font-size:15px;font-weight:700;line-height:1.2;text-decoration:none;border-radius:10px;background-color:{GOLD};border:1px solid {GOLD_DARK};">
                  {safe_label}
                </a>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>"""


def text_link_row(links: list[tuple[str, str]]) -> str:
    """Readable secondary links (no button styling)."""
    parts = []
    for href, label in links:
        parts.append(
            f'<a href="{_esc(href)}" target="_blank" rel="noopener noreferrer" '
            f'style="color:{GOLD_LIGHT};font-size:14px;font-weight:600;text-decoration:underline;">{_esc(label)}</a>'
        )
    joined = f' <span style="color:{TEXT_MUTED};">|</span> '.join(parts)
    return f"""
    <p style="margin:0;text-align:center;font-size:14px;line-height:1.8;color:{TEXT_SECONDARY};">
      {joined}
    </p>"""


def follow_up_box(ref_code: str) -> str:
    if not ref_code:
        return ""
    base = frontend_base()
    track_url = f"{base}/support/ticket?ref={_esc(ref_code)}"
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 20px;">
      <tr>
        <td style="background-color:#1a1a20;border:1px solid {BORDER};border-radius:10px;padding:16px 18px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{GOLD};margin-bottom:8px;">Track your request</div>
          <p style="margin:0 0 10px;font-size:14px;line-height:1.6;color:{TEXT_SECONDARY};">
            Use reference <strong style="color:{TEXT_PRIMARY};">{_esc(ref_code)}</strong> to view updates and add details
            on our support portal (email verification required):
          </p>
          {primary_button(track_url, "View support ticket")}
          <p style="margin:12px 0 0;font-size:12px;line-height:1.5;color:{TEXT_MUTED};">
            You can also reply to this email or contact <a href="mailto:support@rajverse.me" style="color:{GOLD_LIGHT};">support@rajverse.me</a>.
          </p>
        </td>
      </tr>
    </table>"""


def contact_admin_html(submission: Dict) -> str:
    ref_code = reference_code(submission)
    ref_line = f" · {ref_code}" if ref_code else ""
    category = subject_label(submission.get("subject", ""))
    ts = format_timestamp(submission.get("timestamp", datetime.utcnow()))

    body = f"""
    <p style="margin:0 0 18px;color:{TEXT_SECONDARY};">
      A new message was submitted through the public contact form{ref_line}.
      Reply directly to this email to reach the sender.
    </p>
    {field_row("Reference", f'<span style="font-size:16px;font-weight:800;letter-spacing:0.05em;color:{GOLD_LIGHT};">{_esc(ref_code)}</span>') if ref_code else ""}
    {field_row("From", _esc(submission["name"]))}
    {field_row("Email", f'<a href="mailto:{_esc(submission["email"])}" style="color:{GOLD_LIGHT};text-decoration:none;">{_esc(submission["email"])}</a>')}
    {field_row("Category", _esc(category))}
    {field_row("Subject line", _esc(submission.get("subject", "")))}
    {field_row("Message", f'<div style="white-space:pre-wrap;">{_esc(submission["message"])}</div>')}
    {field_row("Received", _esc(ts))}
  """

    return zenith_email_html(
        preheader=f"New contact form: {category} from {submission['name']}",
        eyebrow="Internal notification",
        title="New contact form submission",
        body_html=body,
        footer_note="Zenith admin notification — do not forward externally",
    )


def contact_admin_text(submission: Dict) -> str:
    ref_code = reference_code(submission)
    ref_line = f"\nReference: {ref_code}" if ref_code else ""
    category = subject_label(submission.get("subject", ""))
    ts = format_timestamp(submission.get("timestamp", datetime.utcnow()))

    return f"""New contact form submission{ref_line}

From: {submission['name']}
Email: {submission['email']}
Category: {category}
Subject key: {submission.get('subject', '')}

Message:
{submission['message']}

Received: {ts}

---
Reply to this email to respond to {submission['name']}.
"""


def contact_auto_reply_html(submission: Dict) -> str:
    base = frontend_base()
    ref_code = reference_code(submission)
    ref_html = (
        f'<span style="color:{GOLD_LIGHT};font-weight:800;letter-spacing:0.05em;">{_esc(ref_code)}</span>'
        if ref_code
        else "your request"
    )
    category = subject_label(submission.get("subject", ""))
    preview = submission["message"][:280]
    if len(submission["message"]) > 280:
        preview += "…"

    body = f"""
    <p style="margin:0 0 14px;color:{TEXT_PRIMARY};font-size:16px;">Hello {_esc(submission['name'])},</p>
    <p style="margin:0 0 16px;color:{TEXT_SECONDARY};">
      Thank you for contacting Zenith. We have received your message and a member of our support team
      will review it shortly.
    </p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 18px;background-color:#1a1a20;border:1px solid {BORDER};border-radius:10px;">
      <tr>
        <td style="padding:14px 16px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{GOLD};margin-bottom:8px;">Your submission</div>
          <div style="font-size:13px;color:{TEXT_MUTED};margin-bottom:6px;">Reference {ref_html} · {_esc(category)}</div>
          <div style="font-size:14px;color:{TEXT_PRIMARY};line-height:1.55;white-space:pre-wrap;">{_esc(preview)}</div>
        </td>
      </tr>
    </table>
    {follow_up_box(ref_code)}
    <p style="margin:0 0 8px;color:{TEXT_SECONDARY};"><strong style="color:{TEXT_PRIMARY};">What happens next</strong></p>
    <ul style="margin:0 0 6px;padding-left:20px;color:{TEXT_SECONDARY};">
      <li style="margin-bottom:6px;">Typical response time: within 24 hours on business days (9 AM – 6 PM IST).</li>
      <li style="margin-bottom:6px;">Urgent billing or security issues are prioritized.</li>
    </ul>
    <p style="margin:0 0 4px;font-size:14px;font-weight:600;color:{TEXT_PRIMARY};">While you wait</p>
    {primary_button(f"{base}/help", "Browse Help Center")}
    {text_link_row([
        (f"{base}/status", "System status"),
        (f"{base}/docs", "Documentation"),
        (f"{base}/contact", "Contact again"),
    ])}
  """

    return zenith_email_html(
        preheader="We received your message and will respond soon.",
        eyebrow="Support confirmation",
        title="We received your message",
        body_html=body,
    )


def contact_auto_reply_text(submission: Dict) -> str:
    base = frontend_base()
    ref_code = reference_code(submission)
    ref_line = f"Reference: {ref_code}\n" if ref_code else ""
    category = subject_label(submission.get("subject", ""))
    preview = submission["message"][:280]
    if len(submission["message"]) > 280:
        preview += "…"

    follow_up = ""
    if ref_code:
        follow_up = f"""
Track your request: {base}/support/ticket?ref={ref_code}
(Verify your email with a one-time code to view the thread.)

"""

    return f"""Hello {submission['name']},

Thank you for contacting Zenith. We have received your message and will respond within 24 hours on business days (9 AM – 6 PM IST).

{ref_line}Category: {category}

Your message:
{preview}
{follow_up}
Helpful links:
- Help Center: {base}/help
- System status: {base}/status
- Documentation: {base}/docs

Best regards,
Zenith Support Team
support@rajverse.me
"""


def ticket_otp_html(ref_code: str, otp: str) -> str:
    body = f"""
    <p style="margin:0 0 14px;color:{TEXT_SECONDARY};">
      Use this verification code to access support ticket <strong style="color:{GOLD_LIGHT};">{_esc(ref_code)}</strong>.
      It expires in 15 minutes.
    </p>
    <table role="presentation" cellspacing="0" cellpadding="0" style="margin:8px 0 0;">
      <tr>
        <td align="center" bgcolor="#0f0f14" style="padding:14px 24px;background-color:#0f0f14;border:2px dashed {GOLD};border-radius:10px;font-size:28px;font-weight:800;letter-spacing:0.2em;color:{GOLD_LIGHT};">
          {_esc(otp)}
        </td>
      </tr>
    </table>
    <p style="margin:16px 0 0;font-size:13px;color:{TEXT_MUTED};">
      If you did not request this code, you can ignore this email.
    </p>
    """
    return zenith_email_html(
        preheader="Your Zenith support verification code",
        eyebrow="Verification",
        title="Support access code",
        body_html=body,
    )


def ticket_otp_text(ref_code: str, otp: str) -> str:
    return f"""Your Zenith support verification code

Ticket: {ref_code}
Code: {otp}

This code expires in 15 minutes.

If you did not request this, ignore this email.
"""


def agent_reply_html(
    *,
    requester_name: str,
    ref_code: str,
    message_preview: str,
    for_logged_in: bool,
) -> str:
    base = frontend_base()
    if for_logged_in:
        cta_url = f"{base}/dashboard/support"
        cta_label = "Open support inbox"
    else:
        cta_url = f"{base}/support/ticket?ref={_esc(ref_code)}"
        cta_label = "View ticket"
    preview = message_preview[:400]
    if len(message_preview) > 400:
        preview += "…"
    body = f"""
    <p style="margin:0 0 14px;color:{TEXT_PRIMARY};font-size:16px;">Hello {_esc(requester_name)},</p>
    <p style="margin:0 0 16px;color:{TEXT_SECONDARY};">
      Our support team replied to your request <strong style="color:{GOLD_LIGHT};">{_esc(ref_code)}</strong>.
    </p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 18px;background-color:#1a1a20;border:1px solid {BORDER};border-radius:10px;">
      <tr><td style="padding:14px 16px;font-size:14px;color:{TEXT_PRIMARY};line-height:1.55;white-space:pre-wrap;">{_esc(preview)}</td></tr>
    </table>
    {primary_button(cta_url, cta_label)}
    """
    return zenith_email_html(
        preheader="New reply from Zenith Support",
        eyebrow="Support update",
        title="We replied to your ticket",
        body_html=body,
    )


def agent_reply_text(
    *,
    requester_name: str,
    ref_code: str,
    message_preview: str,
    for_logged_in: bool,
) -> str:
    base = frontend_base()
    link = f"{base}/dashboard/support" if for_logged_in else f"{base}/support/ticket?ref={ref_code}"
    return f"""Hello {requester_name},

We replied to your support ticket {ref_code}.

{message_preview[:400]}

View the conversation: {link}

Zenith Support Team
"""


def ticket_resolved_html(requester_name: str, ref_code: str) -> str:
    base = frontend_base()
    body = f"""
    <p style="margin:0 0 14px;color:{TEXT_PRIMARY};font-size:16px;">Hello {_esc(requester_name)},</p>
    <p style="margin:0 0 16px;color:{TEXT_SECONDARY};">
      Your support request <strong style="color:{GOLD_LIGHT};">{_esc(ref_code)}</strong> has been marked resolved.
      If you need more help, reply on the ticket page or submit a new message from Contact.
    </p>
    {primary_button(f"{base}/support/ticket?ref={_esc(ref_code)}", "View ticket")}
    """
    return zenith_email_html(
        preheader="Your Zenith support ticket was resolved",
        eyebrow="Support",
        title="Ticket resolved",
        body_html=body,
    )


def ticket_resolved_text(requester_name: str, ref_code: str) -> str:
    base = frontend_base()
    return f"""Hello {requester_name},

Your support ticket {ref_code} has been marked resolved.

Reopen or follow up: {base}/support/ticket?ref={ref_code}

Zenith Support Team
"""


def admin_customer_reply_html(ref_code: str, requester_name: str, preview: str) -> str:
    base = frontend_base()
    body = f"""
    <p style="margin:0 0 14px;color:{TEXT_SECONDARY};">
      <strong style="color:{TEXT_PRIMARY};">{_esc(requester_name)}</strong> added a message to ticket
      <strong style="color:{GOLD_LIGHT};">{_esc(ref_code)}</strong>.
    </p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 18px;background-color:#1a1a20;border:1px solid {BORDER};border-radius:10px;">
      <tr><td style="padding:14px 16px;font-size:14px;color:{TEXT_PRIMARY};line-height:1.55;white-space:pre-wrap;">{_esc(preview[:500])}</td></tr>
    </table>
    {primary_button(f"{base}/admin/support", "Open admin inbox")}
    """
    return zenith_email_html(
        preheader=f"Customer reply on {ref_code}",
        eyebrow="Internal notification",
        title="Customer replied to ticket",
        body_html=body,
        footer_note="Zenith admin notification",
    )


def admin_customer_reply_text(ref_code: str, requester_name: str, preview: str) -> str:
    return f"""Customer reply on ticket {ref_code}

From: {requester_name}

{preview[:500]}

Open admin inbox to respond.
"""


def org_invite_html(
    *,
    org_name: str,
    invite_link: str,
    role: str,
    invited_by: str,
) -> str:
    body = f"""
    <p style="margin:0 0 14px;color:{TEXT_SECONDARY};">
      <strong style="color:{TEXT_PRIMARY};">{_esc(invited_by)}</strong> invited you to join
      <strong style="color:{GOLD_LIGHT};">{_esc(org_name)}</strong> on Zenith as
      <strong>{_esc(role)}</strong>.
    </p>
    <p style="margin:0 0 18px;color:{TEXT_SECONDARY};font-size:14px;">
      This link expires in 7 days. Sign in with the email address that received this invite.
    </p>
    {primary_button(invite_link, "Accept invitation")}
    """
    return zenith_email_html(
        preheader=f"Join {org_name} on Zenith",
        eyebrow="Team invitation",
        title="You're invited to a team workspace",
        body_html=body,
        footer_note="If you did not expect this invite, you can ignore this email.",
    )


def org_invite_text(*, org_name: str, invite_link: str, role: str, invited_by: str) -> str:
    return f"""You're invited to join {org_name} on Zenith

{invited_by} invited you as {role}.

Accept invitation: {invite_link}

This link expires in 7 days. Sign in with the email address that received this invite.
"""


def org_budget_alert_html(
    *,
    org_name: str,
    spend_usd: float,
    budget_usd: float,
    status: str,
) -> str:
    base = frontend_base()
    label = "exceeded" if status == "exceeded" else "approaching"
    body = f"""
    <p style="margin:0 0 14px;color:{TEXT_SECONDARY};">
      Team cloud spend for <strong style="color:{TEXT_PRIMARY};">{_esc(org_name)}</strong> is
      <strong style="color:{GOLD_LIGHT};">{label}</strong> your monthly org budget.
    </p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 18px;">
      <tr><td style="padding:8px 0;color:{TEXT_MUTED};font-size:13px;">Current spend</td>
          <td style="padding:8px 0;text-align:right;color:{TEXT_PRIMARY};font-weight:600;">${_esc(f'{spend_usd:.2f}')}</td></tr>
      <tr><td style="padding:8px 0;color:{TEXT_MUTED};font-size:13px;">Monthly budget</td>
          <td style="padding:8px 0;text-align:right;color:{TEXT_PRIMARY};font-weight:600;">${_esc(f'{budget_usd:.2f}')}</td></tr>
    </table>
    {primary_button(f"{base}/dashboard/team", "Review team spend")}
    """
    return zenith_email_html(
        preheader=f"{org_name} budget {label}",
        eyebrow="Org budget alert",
        title=f"Team budget {label}",
        body_html=body,
        footer_note="Billing remains per Zenith account; this is a team visibility alert.",
    )


def org_budget_alert_text(
    *, org_name: str, spend_usd: float, budget_usd: float, status: str
) -> str:
    label = "exceeded" if status == "exceeded" else "approaching"
    return f"""Team budget alert — {org_name}

Team spend is {label} your monthly org budget.

Current spend: ${spend_usd:.2f}
Monthly budget: ${budget_usd:.2f}

Review: {frontend_base()}/dashboard/team
"""

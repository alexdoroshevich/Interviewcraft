"""Email service — async-compatible SMTP using a thread-pool executor.

Sends weekly digest emails summarising the user's interview progress.
SMTP is optional: if SMTP_HOST is empty the service is a no-op (logs a
warning instead of sending) so the app runs fine without email configured.

No new pip dependencies — uses Python stdlib: smtplib, ssl, email.mime.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial

import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)


def _mask_email(email: str) -> str:
    """Mask email address for safe logging: alice@example.com → a***@example.com."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}" if local else f"***@{domain}"


# ── Data class for digest content ─────────────────────────────────────────────


class DigestStats:
    """Stats bundle passed to build_digest_html()."""

    def __init__(
        self,
        *,
        user_email: str,
        sessions_this_week: int,
        sessions_total: int,
        avg_score_this_week: float | None,
        avg_score_all_time: float | None,
        top_weaknesses: list[tuple[str, int]],  # [(skill_name, score), ...]
        due_for_review: list[str],  # skill names
        sessions_completed_total: int,
    ) -> None:
        self.user_email = user_email
        self.sessions_this_week = sessions_this_week
        self.sessions_total = sessions_total
        self.avg_score_this_week = avg_score_this_week
        self.avg_score_all_time = avg_score_all_time
        self.top_weaknesses = top_weaknesses
        self.due_for_review = due_for_review
        self.sessions_completed_total = sessions_completed_total


# ── HTML builder ─────────────────────────────────────────────────────────────

_SKILL_LABELS: dict[str, str] = {
    "star_structure": "STAR Structure",
    "quantifiable_results": "Quantifiable Results",
    "ownership_signal": "Ownership Signal",
    "conflict_resolution": "Conflict Resolution",
    "leadership_stories": "Leadership Stories",
    "mentoring_signal": "Mentoring Signal",
    "capacity_estimation": "Capacity Estimation",
    "tradeoff_analysis": "Tradeoff Analysis",
    "component_design": "Component Design",
    "api_design": "API Design",
    "scalability_thinking": "Scalability Thinking",
    "failure_modes": "Failure Modes",
    "conciseness": "Conciseness",
    "filler_word_control": "Filler Word Control",
    "pacing": "Pacing",
    "confidence_under_pressure": "Confidence Under Pressure",
    "complexity_analysis": "Complexity Analysis",
    "edge_cases": "Edge Cases",
    "testing_approach": "Testing Approach",
    "code_review_reasoning": "Code Review Reasoning",
    "anchoring": "Anchoring",
    "value_articulation": "Value Articulation",
    "counter_strategy": "Counter Strategy",
    "emotional_control": "Emotional Control",
}


def _skill_label(name: str) -> str:
    return _SKILL_LABELS.get(name, name.replace("_", " ").title())


def _score_bar(score: int, width: int = 200) -> str:
    """Return an HTML progress bar for a 0-100 score."""
    pct = max(0, min(100, score))
    if pct >= 70:
        color = "#22c55e"
    elif pct >= 50:
        color = "#f59e0b"
    else:
        color = "#ef4444"
    filled = int(width * pct / 100)
    return (
        f'<div style="background:#e2e8f0;border-radius:4px;width:{width}px;height:8px;'
        f'display:inline-block;vertical-align:middle;">'
        f'<div style="background:{color};border-radius:4px;width:{filled}px;height:8px;"></div>'
        f"</div>"
    )


def build_digest_html(stats: DigestStats, app_url: str = "http://localhost:3000") -> str:
    """Build the weekly digest email HTML.

    Args:
        stats: Pre-computed user stats.
        app_url: Root URL for CTA links.

    Returns:
        HTML string suitable for an email body.
    """
    week_score_str = (
        f"{stats.avg_score_this_week:.0f}" if stats.avg_score_this_week is not None else "—"
    )
    all_score_str = (
        f"{stats.avg_score_all_time:.0f}" if stats.avg_score_all_time is not None else "—"
    )

    # ── Weakness rows ──────────────────────────────────────────────────────────
    weakness_rows = ""
    for skill_name, score in stats.top_weaknesses[:3]:
        bar = _score_bar(score)
        label = _skill_label(skill_name)
        weakness_rows += (
            f'<tr><td style="padding:6px 0;color:#334155;font-size:14px;">{label}</td>'
            f'<td style="padding:6px 12px;text-align:right;font-weight:600;'
            f'color:#64748b;font-size:13px;">{score}</td>'
            f'<td style="padding:6px 0;">{bar}</td></tr>'
        )
    if not weakness_rows:
        weakness_rows = (
            '<tr><td colspan="3" style="color:#94a3b8;font-size:14px;padding:8px 0;">'
            "No skill data yet — complete a session to see your scores.</td></tr>"
        )

    # ── Review pills ──────────────────────────────────────────────────────────
    review_pills = ""
    for skill_name in stats.due_for_review[:5]:
        label = _skill_label(skill_name)
        review_pills += (
            f'<span style="display:inline-block;background:#ede9fe;color:#7c3aed;'
            f"border-radius:9999px;padding:3px 10px;font-size:12px;"
            f'margin:2px 3px 2px 0;">{label}</span>'
        )
    if not review_pills:
        review_pills = (
            '<span style="color:#94a3b8;font-size:14px;">Nothing due — keep it up!</span>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr><td style="padding:32px 40px 24px;border-bottom:1px solid #e2e8f0;">
          <div style="color:#6366f1;font-size:13px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;">InterviewCraft</div>
          <h1 style="margin:8px 0 4px;font-size:22px;color:#0f172a;">Your Weekly Practice Digest</h1>
          <p style="margin:0;color:#64748b;font-size:14px;">Stay on track for your next big offer.</p>
        </td></tr>

        <!-- Stats row -->
        <tr><td style="padding:28px 40px 20px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="33%" style="text-align:center;padding:0 8px;">
                <div style="font-size:32px;font-weight:700;color:#6366f1;">{stats.sessions_this_week}</div>
                <div style="font-size:12px;color:#64748b;margin-top:2px;">Sessions this week</div>
              </td>
              <td width="33%" style="text-align:center;padding:0 8px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
                <div style="font-size:32px;font-weight:700;color:#0f172a;">{week_score_str}</div>
                <div style="font-size:12px;color:#64748b;margin-top:2px;">Avg score this week</div>
              </td>
              <td width="33%" style="text-align:center;padding:0 8px;">
                <div style="font-size:32px;font-weight:700;color:#0f172a;">{all_score_str}</div>
                <div style="font-size:12px;color:#64748b;margin-top:2px;">All-time avg score</div>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Weaknesses -->
        <tr><td style="padding:0 40px 24px;">
          <h2 style="margin:0 0 12px;font-size:16px;color:#0f172a;">Top areas to improve</h2>
          <table width="100%" cellpadding="0" cellspacing="0">
            {weakness_rows}
          </table>
        </td></tr>

        <!-- Due for review -->
        <tr><td style="padding:0 40px 28px;border-top:1px solid #e2e8f0;">
          <h2 style="margin:16px 0 10px;font-size:16px;color:#0f172a;">Due for review</h2>
          <div>{review_pills}</div>
        </td></tr>

        <!-- CTA -->
        <tr><td style="padding:0 40px 36px;text-align:center;">
          <a href="{app_url}/sessions/new"
             style="display:inline-block;background:#6366f1;color:#ffffff;text-decoration:none;
                    font-size:15px;font-weight:600;padding:12px 32px;border-radius:8px;">
            Start a Drill Session →
          </a>
          <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;">
            You've completed <strong>{stats.sessions_total}</strong> sessions total.
            Keep the streak going!
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 40px;border-top:1px solid #e2e8f0;text-align:center;">
          <p style="margin:0;font-size:11px;color:#94a3b8;">
            You're receiving this because you opted in to weekly digests.<br>
            <a href="{app_url}/settings" style="color:#6366f1;text-decoration:none;">Manage email preferences</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── SMTP sender ───────────────────────────────────────────────────────────────


def _send_email_sync(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    config: Settings,
) -> None:
    """Blocking SMTP send — run in executor to keep async loop free."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.smtp_from_name} <{config.smtp_from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    if config.smtp_tls:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            if config.smtp_username:
                smtp.login(config.smtp_username, config.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP_SSL(
            config.smtp_host, config.smtp_port, context=context, timeout=15
        ) as smtp:
            if config.smtp_username:
                smtp.login(config.smtp_username, config.smtp_password)
            smtp.send_message(msg)


async def send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    config: Settings,
) -> bool:
    """Send an HTML email asynchronously.

    Returns True on success, False if SMTP not configured or send failed.
    Never raises — logs errors instead.
    """
    if not config.smtp_host:
        logger.warning("email.smtp_not_configured", to=_mask_email(to_email), subject=subject)
        return False

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            partial(
                _send_email_sync,
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                config=config,
            ),
        )
        logger.info("email.sent", to=_mask_email(to_email), subject=subject)
        return True
    except Exception as exc:
        logger.error("email.send_failed", to=_mask_email(to_email), error=str(exc))
        return False

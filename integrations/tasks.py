from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import timedelta
import io
from core.logger import logger


@shared_task
def send_daily_call_report():
    """
    Runs every day at 8 AM.
    Finds all users with Google Sheets integration connected
    and sends them a daily call report email with an Excel attachment.
    """
    from integrations.models import Integration
    from calls.models import CallLog

    yesterday_start = timezone.now() - timedelta(days=1)

    connected = Integration.objects.filter(
        type="google_sheets",
        is_connected=True,
    ).select_related("user")

    for integration in connected:
        user  = integration.user
        calls = CallLog.objects.filter(
            agent__owner=user,
            created_at__gte=yesterday_start,
        ).select_related("agent")

        total     = calls.count()
        completed = calls.filter(status="completed").count()
        failed    = calls.filter(status="failed").count()
        booked    = calls.filter(outcome="booked").count()

        durations    = list(calls.filter(duration_seconds__gt=0).values_list("duration_seconds", flat=True))
        avg_dur_sec  = int(sum(durations) / len(durations)) if durations else 0
        avg_dur_str  = f"{avg_dur_sec // 60}m {avg_dur_sec % 60}s"

        # ── build Excel file in memory ─────────────────────────────────────────
        excel_data = _build_excel(calls, yesterday_start)

        date_str    = timezone.now().strftime("%d %b %Y")
        subject     = f"VoiceAI Daily Report — {date_str}"
        name        = user.first_name or user.email.split("@")[0].capitalize()
        html_body   = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>VoiceAI Daily Report</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="580" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#4f6ef7 0%,#6366f1 100%);padding:32px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <span style="font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">&#9742; VoiceAI</span>
                  </td>
                  <td align="right">
                    <span style="font-size:12px;color:rgba(255,255,255,0.75);font-weight:500;">Daily Report</span>
                  </td>
                </tr>
              </table>
              <div style="margin-top:20px;">
                <div style="font-size:24px;font-weight:700;color:#ffffff;margin-bottom:4px;">Good morning, {name} 👋</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.80);">Here's your call performance summary for <strong>{date_str}</strong></div>
              </div>
            </td>
          </tr>

          <!-- Stats grid -->
          <tr>
            <td style="padding:32px 40px 8px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="48%" style="background:#f8fafc;border:1px solid #e8edf2;border-radius:10px;padding:20px 22px;vertical-align:top;">
                    <div style="font-size:11px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Total Calls</div>
                    <div style="font-size:32px;font-weight:700;color:#0f172a;line-height:1;">{total}</div>
                  </td>
                  <td width="4%"></td>
                  <td width="48%" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:20px 22px;vertical-align:top;">
                    <div style="font-size:11px;font-weight:600;color:#16a34a;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Completed</div>
                    <div style="font-size:32px;font-weight:700;color:#15803d;line-height:1;">{completed}</div>
                  </td>
                </tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">
                <tr>
                  <td width="48%" style="background:#fff1f2;border:1px solid #fecdd3;border-radius:10px;padding:20px 22px;vertical-align:top;">
                    <div style="font-size:11px;font-weight:600;color:#e11d48;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Failed</div>
                    <div style="font-size:32px;font-weight:700;color:#be123c;line-height:1;">{failed}</div>
                  </td>
                  <td width="4%"></td>
                  <td width="48%" style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:20px 22px;vertical-align:top;">
                    <div style="font-size:11px;font-weight:600;color:#3b82f6;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Appointments Booked</div>
                    <div style="font-size:32px;font-weight:700;color:#1d4ed8;line-height:1;">{booked}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Avg duration row -->
          <tr>
            <td style="padding:12px 40px 32px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#fefce8;border:1px solid #fef08a;border-radius:10px;padding:16px 22px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <div style="font-size:11px;font-weight:600;color:#a16207;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:2px;">Avg Call Duration</div>
                          <div style="font-size:20px;font-weight:700;color:#854d0e;">{avg_dur_str}</div>
                        </td>
                        <td align="right" style="font-size:28px;">&#9200;</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <div style="height:1px;background:#f1f5f9;"></div>
            </td>
          </tr>

          <!-- Attachment note -->
          <tr>
            <td style="padding:24px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#f8fafc;border:1px solid #e8edf2;border-radius:8px;padding:14px 18px;">
                    <table cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="font-size:20px;padding-right:12px;">&#128202;</td>
                        <td>
                          <div style="font-size:13px;font-weight:600;color:#0f172a;">Full Call Log Attached</div>
                          <div style="font-size:12px;color:#64748b;margin-top:2px;">Excel file with all call details, outcomes, and sentiment scores</div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8fafc;border-top:1px solid #f1f5f9;padding:20px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <div style="font-size:12px;color:#94a3b8;">Sent by <strong style="color:#64748b;">VoiceAI</strong> · Daily report every morning at 8 AM</div>
                    <div style="font-size:11px;color:#cbd5e1;margin-top:4px;">To stop receiving these emails, disconnect Google Sheets from your integrations.</div>
                  </td>
                  <td align="right">
                    <span style="font-size:18px;">&#9742;</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        try:
            email = EmailMessage(
                subject    = subject,
                body       = html_body,
                from_email = settings.DEFAULT_FROM_EMAIL,
                to         = [user.email],
            )
            email.content_subtype = "html"
            email.attach(
                filename = f"call_report_{timezone.now().strftime('%Y-%m-%d')}.xlsx",
                content  = excel_data,
                mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            email.send(fail_silently=False)
            logger.info(f"[DAILY REPORT] Sent to {user.email} — {total} calls")
        except Exception as e:
            logger.error(f"[DAILY REPORT] Failed for {user.email}: {e}")


def _build_excel(calls, since):
    """Build an in-memory Excel workbook from the call queryset and return bytes."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        # openpyxl not installed — return empty bytes, email body still sends
        logger.warning("[DAILY REPORT] openpyxl not installed, skipping Excel attachment")
        return b""

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Call Report"

    # header row
    headers = ["#", "Date", "Caller", "Agent", "Duration", "Status", "Outcome", "Sentiment"]
    header_fill = PatternFill("solid", fgColor="4F6EF7")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill   = header_fill
        cell.font   = header_font
        cell.alignment = Alignment(horizontal="center")

    # data rows
    for row_idx, call in enumerate(calls, 2):
        dur = f"{call.duration_seconds // 60}m {call.duration_seconds % 60}s" if call.duration_seconds else "—"
        ws.append([
            row_idx - 1,
            call.created_at.strftime("%Y-%m-%d %H:%M") if call.created_at else "—",
            call.caller_phone,
            call.agent.agent_name if call.agent else "—",
            dur,
            call.status,
            call.outcome,
            round(call.sentiment_score, 2) if call.sentiment_score is not None else "—",
        ])

    # auto column width
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

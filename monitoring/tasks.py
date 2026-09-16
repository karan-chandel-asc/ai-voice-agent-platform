"""Celery tasks for Deskline outreach visit reports."""
from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Count
from django.utils import timezone

from core.logger import logger


@shared_task(name="monitoring.tasks.send_daily_outreach_visit_report")
def send_daily_outreach_visit_report():
    """
    Every morning at 8:00 (CELERY_TIMEZONE): email who opened Deskline
    and from which country (last 24 hours).
    """
    from monitoring.models import ProjectVisit

    to_email = (
        getattr(settings, "OUTREACH_REPORT_EMAIL", "") or ""
    ).strip() or (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    if not to_email:
        logger.warning("[OUTREACH VISITS] No OUTREACH_REPORT_EMAIL / EMAIL_HOST_USER set — skip")
        return "no-recipient"

    since = timezone.now() - timedelta(hours=24)
    visits = list(
        ProjectVisit.objects.filter(visited_at__gte=since).order_by("-visited_at")
    )
    total = len(visits)
    unique_ips = len({v.ip_address for v in visits if v.ip_address})
    by_country = (
        ProjectVisit.objects.filter(visited_at__gte=since)
        .values("country")
        .annotate(n=Count("id"))
        .order_by("-n")
    )

    date_str = timezone.now().strftime("%d %b %Y")
    subject = f"Deskline outreach opens — {date_str} ({unique_ips} people)"

    country_rows = ""
    for row in by_country:
        country = row["country"] or "Unknown"
        country_rows += f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#0f172a;">{country}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#0f172a;text-align:right;font-weight:600;">{row['n']}</td>
        </tr>"""
    if not country_rows:
        country_rows = """
        <tr>
          <td colspan="2" style="padding:14px;font-size:13px;color:#94a3b8;">No visits in the last 24 hours.</td>
        </tr>"""

    detail_rows = ""
    for v in visits[:50]:
        when = timezone.localtime(v.visited_at).strftime("%H:%M")
        where = v.country or "Unknown"
        if v.city:
            where = f"{v.city}, {where}"
        detail_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f8fafc;font-size:12px;color:#64748b;">{when}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f8fafc;font-size:12px;color:#0f172a;">{where}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f8fafc;font-size:12px;color:#64748b;">{v.path or '/'}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f8fafc;font-size:12px;color:#94a3b8;">{v.ip_address or '—'}</td>
        </tr>"""
    if not detail_rows:
        detail_rows = """
        <tr><td colspan="4" style="padding:14px;font-size:13px;color:#94a3b8;">No opens recorded.</td></tr>"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><title>Deskline Opens</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:linear-gradient(135deg,#16332B 0%,#1F4839 100%);padding:28px 36px;">
            <div style="font-size:18px;font-weight:700;color:#F6F1E4;">Deskline</div>
            <div style="font-size:22px;font-weight:700;color:#ffffff;margin-top:12px;">Good morning 👋</div>
            <div style="font-size:13px;color:rgba(246,241,228,0.85);margin-top:4px;">
              Who opened the project in the last 24 hours · {date_str}
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 36px 8px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="48%" style="background:#f8fafc;border:1px solid #e8edf2;border-radius:10px;padding:18px 20px;">
                  <div style="font-size:11px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;">Unique people</div>
                  <div style="font-size:30px;font-weight:700;color:#16332B;">{unique_ips}</div>
                </td>
                <td width="4%"></td>
                <td width="48%" style="background:#F0E6D4;border:1px solid #C9A46E;border-radius:10px;padding:18px 20px;">
                  <div style="font-size:11px;font-weight:600;color:#A9814A;text-transform:uppercase;letter-spacing:0.06em;">Total opens</div>
                  <div style="font-size:30px;font-weight:700;color:#16332B;">{total}</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 36px 8px;">
            <div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:10px;">By country</div>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8edf2;border-radius:10px;overflow:hidden;">
              <tr style="background:#fafbfc;">
                <th align="left" style="padding:10px 14px;font-size:11px;color:#94a3b8;text-transform:uppercase;">Country</th>
                <th align="right" style="padding:10px 14px;font-size:11px;color:#94a3b8;text-transform:uppercase;">Opens</th>
              </tr>
              {country_rows}
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 36px 28px;">
            <div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:10px;">Recent opens</div>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8edf2;border-radius:10px;overflow:hidden;">
              <tr style="background:#fafbfc;">
                <th align="left" style="padding:8px 12px;font-size:11px;color:#94a3b8;">Time</th>
                <th align="left" style="padding:8px 12px;font-size:11px;color:#94a3b8;">Country</th>
                <th align="left" style="padding:8px 12px;font-size:11px;color:#94a3b8;">Page</th>
                <th align="left" style="padding:8px 12px;font-size:11px;color:#94a3b8;">IP</th>
              </tr>
              {detail_rows}
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #f1f5f9;padding:16px 36px;font-size:12px;color:#94a3b8;">
            Deskline outreach tracker · daily email at 8:00 AM ({settings.TIME_ZONE})
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        email = EmailMessage(
            subject=subject,
            body=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        logger.info(f"[OUTREACH VISITS] Sent to {to_email} — {unique_ips} unique / {total} opens")
        return f"sent:{unique_ips}/{total}"
    except Exception as exc:
        logger.error(f"[OUTREACH VISITS] Failed for {to_email}: {exc}")
        raise

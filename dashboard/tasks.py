from django.core.mail import EmailMessage
from django.conf import settings
from core.logger import logger


def send_booking_confirmation_email(booking):
    """Send a booking confirmation email to the guest."""
    try:
        name = booking.guest_name
        guests = booking.guests
        check_in = booking.check_in.strftime("%A, %B %d, %Y") if booking.check_in else "—"
        check_out = booking.check_out.strftime("%A, %B %d, %Y") if booking.check_out else "—"
        btype = "Room" if booking.booking_type == "room" else "Table"

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Booking Confirmed</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:linear-gradient(135deg,#0F766E 0%,#0D9488 100%);padding:32px 40px;">
            <div style="font-size:20px;font-weight:700;color:#ffffff;">Deskline</div>
            <div style="margin-top:16px;font-size:24px;font-weight:700;color:#ffffff;">Booking Confirmed</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.80);margin-top:6px;">Hi {name}, your {btype.lower()} reservation is confirmed.</div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e8edf2;border-radius:10px;padding:24px 28px;">
              <tr>
                <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:12px;color:#94a3b8;">Type</td>
                <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right;font-size:13px;font-weight:600;">{btype}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:12px;color:#94a3b8;">Check-in</td>
                <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right;font-size:13px;font-weight:600;">{check_in}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:12px;color:#94a3b8;">Check-out</td>
                <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right;font-size:13px;font-weight:600;">{check_out}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;font-size:12px;color:#94a3b8;">Guests</td>
                <td style="padding:8px 0;text-align:right;font-size:13px;font-weight:600;">{guests}</td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #f1f5f9;padding:20px 40px;">
            <div style="font-size:12px;color:#94a3b8;">Sent by <strong style="color:#64748b;">Deskline</strong></div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

        to_email = booking.guest_email
        if not to_email:
            logger.warning(f"[BOOKING CONFIRM] No guest email for booking {booking.id}, skipping.")
            return

        email = EmailMessage(
            subject=f"Booking Confirmed — {name} · {check_in}",
            body=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        logger.info(f"[BOOKING CONFIRM] Email sent to guest {to_email} for {name}")
    except Exception as e:
        logger.error(f"[BOOKING CONFIRM] Email failed: {e}")

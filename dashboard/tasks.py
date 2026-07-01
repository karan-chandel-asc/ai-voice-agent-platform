from django.core.mail import EmailMessage
from django.conf import settings
from core.logger import logger


def send_booking_confirmation_email(booking):
    """Send a booking confirmation email to the guest."""
    guest_email = booking.phone  # phone field is used — if you add email field later, switch here
    # Try to get user email from agent owner as fallback sender context
    try:
        name = booking.guest_name
        date_str = booking.date.strftime("%A, %B %d, %Y")
        time_str = booking.time.strftime("%I:%M %p")
        guests = booking.guests

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Booking Confirmed</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#4f6ef7 0%,#6366f1 100%);padding:32px 40px;">
            <div style="font-size:20px;font-weight:700;color:#ffffff;">&#9742; VoiceAI</div>
            <div style="margin-top:16px;font-size:24px;font-weight:700;color:#ffffff;">Booking Confirmed &#10003;</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.80);margin-top:6px;">Hi {name}, your reservation has been confirmed!</div>
          </td>
        </tr>

        <!-- Details -->
        <tr>
          <td style="padding:32px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#f8fafc;border:1px solid #e8edf2;border-radius:10px;padding:24px 28px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
                        <span style="font-size:12px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Date</span>
                      </td>
                      <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right;">
                        <span style="font-size:13px;font-weight:600;color:#0f172a;">{date_str}</span>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
                        <span style="font-size:12px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Time</span>
                      </td>
                      <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right;">
                        <span style="font-size:13px;font-weight:600;color:#0f172a;">{time_str}</span>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
                        <span style="font-size:12px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Guests</span>
                      </td>
                      <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right;">
                        <span style="font-size:13px;font-weight:600;color:#0f172a;">{guests}</span>
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
            <div style="font-size:12px;color:#94a3b8;">Sent by <strong style="color:#64748b;">VoiceAI</strong></div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

        # Send to the guest's email
        to_email = booking.guest_email
        if not to_email:
            logger.warning(f"[BOOKING CONFIRM] No guest email for booking {booking.id}, skipping.")
            return

        email = EmailMessage(
            subject=f"Booking Confirmed — {name} on {date_str}",
            body=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        logger.info(f"[BOOKING CONFIRM] Email sent to guest {to_email} for {name}")
    except Exception as e:
        logger.error(f"[BOOKING CONFIRM] Email failed: {e}")

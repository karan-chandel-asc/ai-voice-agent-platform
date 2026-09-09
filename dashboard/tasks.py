from django.core.mail import EmailMessage
from django.conf import settings
from core.logger import logger


def send_booking_confirmation_email(booking):
    """Send a full booking-details confirmation email to the guest."""
    try:
        to_email = (booking.guest_email or "").strip()
        if not to_email:
            logger.warning(f"[BOOKING CONFIRM] No guest email for booking {booking.id}, skipping.")
            return False

        name = booking.guest_name or "Guest"
        guests = booking.guests
        check_in = booking.check_in.strftime("%A, %B %d, %Y") if booking.check_in else "—"
        check_out = booking.check_out.strftime("%A, %B %d, %Y") if booking.check_out else "—"
        res_time = (
            booking.reservation_date_time.strftime("%H:%M")
            if booking.reservation_date_time
            else None
        )
        btype = "Room" if booking.booking_type == "room" else "Table"
        room_type = booking.room_type or "—"
        phone = booking.guest_phone or "—"
        nights = booking.nights if booking.nights is not None else "—"
        total = f"${booking.total_price}" if booking.total_price is not None else "—"
        special = booking.special_requests or "None"
        booking_id = str(booking.id)
        property_name = ""
        if booking.agent_id and getattr(booking.agent, "owner", None):
            property_name = booking.agent.owner.business_name or ""
        property_line = property_name or "Deskline"

        rows = [
            ("Booking ID", booking_id),
            ("Type", btype),
            ("Guest name", name),
            ("Email", to_email),
            ("Phone", phone),
            ("Room type", room_type) if booking.booking_type == "room" else None,
            ("Check-in", check_in) if booking.booking_type == "room" else None,
            ("Reservation date", check_in) if booking.booking_type == "table" else None,
            ("Reservation time", res_time) if booking.booking_type == "table" and res_time else None,
            ("Check-out", check_out) if booking.booking_type == "room" else None,
            ("Nights", str(nights)) if booking.booking_type == "room" else None,
            ("Guests", str(guests)),
            ("Total", total) if booking.booking_type == "room" else None,
            ("Special requests", special) if booking.booking_type == "room" else None,
        ]
        rows = [r for r in rows if r]

        detail_rows_html = ""
        for i, (label, value) in enumerate(rows):
            border = "border-bottom:1px solid #f1f5f9;" if i < len(rows) - 1 else ""
            detail_rows_html += f"""
              <tr>
                <td style="padding:8px 0;{border}font-size:12px;color:#94a3b8;">{label}</td>
                <td style="padding:8px 0;{border}text-align:right;font-size:13px;font-weight:600;color:#0f172a;">{value}</td>
              </tr>"""

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Booking Confirmed</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:linear-gradient(135deg,#16332B 0%,#A9814A 100%);padding:32px 40px;">
            <div style="font-size:20px;font-weight:700;color:#ffffff;">Deskline</div>
            <div style="margin-top:16px;font-size:24px;font-weight:700;color:#ffffff;">Booking Confirmed</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-top:6px;">Hi {name}, your {btype.lower()} reservation at {property_line} is confirmed.</div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e8edf2;border-radius:10px;padding:8px 28px;">
              {detail_rows_html}
            </table>
            <p style="margin:20px 0 0;font-size:12px;color:#64748b;line-height:1.5;">
              Please keep this email for your records. If you need to change or cancel, contact the property with your booking ID.
            </p>
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

        email = EmailMessage(
            subject=f"Booking Confirmed — {name} · {check_in}",
            body=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        logger.info(f"[BOOKING CONFIRM] Email sent to guest {to_email} for booking {booking.id}")
        return True
    except Exception as e:
        logger.error(f"[BOOKING CONFIRM] Email failed: {e}")
        return False

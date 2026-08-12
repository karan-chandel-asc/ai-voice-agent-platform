from django.db.models import Avg, Q
from django.utils import timezone
from django.shortcuts import render
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response

from core.auth_utils import RenderAPIView
from core.pagination import Pagination
from core.response_schemas import success_response
from core.logger import logger
from calls.models import CallLog
from agents.models import Agent, Booking

from .serializers import (
    BookingCallSerializer,
    BookingSerializer,
    DashboardStatsSerializer,
    BookingStatsSerializer,
)


class DashboardStatsView(APIView):
    def get(self, request):
        try:
            now    = timezone.now()
            month  = now - timedelta(days=30)
            agents = Agent.objects.filter(owner=request.user)
            calls  = CallLog.objects.filter(agent__owner=request.user)
            bookings_qs = Booking.objects.filter(agent__owner=request.user)

            data = {
                "total_agents":         agents.count(),
                "live_agents":          agents.filter(status="live").count(),
                "total_calls":          calls.filter(created_at__gte=month).count(),
                "room_bookings":        bookings_qs.filter(booking_type="room",  created_at__gte=month).count(),
                "table_bookings":       bookings_qs.filter(booking_type="table", created_at__gte=month).count(),
                "avg_duration_seconds": calls.aggregate(avg=Avg("duration_seconds"))["avg"] or 0,
            }
            serializer = DashboardStatsSerializer(data)
            return Response(success_response(data=serializer.data, message="Dashboard stats fetched"))
        except Exception as e:
            logger.error(f"DashboardStatsView error: {e}")
            return Response(success_response(message="Something went wrong"), status=500)


class BookingsView(APIView):
    def get(self, request):
        try:
            now   = timezone.now()
            month = now - timedelta(days=30)

            all_bookings_qs = Booking.objects.filter(agent__owner=request.user)

            stats_data = {
                "total_booking":      all_bookings_qs.count(),
                "rooms_booking":      all_bookings_qs.filter(booking_type="room").count(),
                "tables":             all_bookings_qs.filter(booking_type="table").count(),
                "this_month": all_bookings_qs.filter(created_at__gte=month).count(),
                "avg_duration":  0,
                "avg_sentiment": 0,
            }
            stats = BookingStatsSerializer(stats_data).data

            # ── filtered queryset ──────────────────────────────────────────────
            qs = all_bookings_qs.select_related("agent").order_by("-created_at")

            agent_id     = request.query_params.get("agent")
            date_from    = request.query_params.get("from")
            date_to      = request.query_params.get("to")
            search       = request.query_params.get("search", "").strip()
            booking_type = request.query_params.get("booking_type", "").strip()
            confirmed    = request.query_params.get("confirmed", "").strip()

            if agent_id:
                qs = qs.filter(agent_id=agent_id)
            if date_from:
                qs = qs.filter(check_in__gte=date_from)
            if date_to:
                qs = qs.filter(check_in__lte=date_to)
            if booking_type in ("room", "table"):
                qs = qs.filter(booking_type=booking_type)
            if confirmed in ("0", "1"):
                qs = qs.filter(is_confirmed=bool(int(confirmed)))
            if search:
                qs = qs.filter(
                    Q(guest_name__icontains=search) |
                    Q(guest_email__icontains=search) |
                    Q(agent__agent_name__icontains=search)
                )

            # ── DRF pagination ─────────────────────────────────────────────────
            paginator = Pagination()
            page = paginator.paginate_queryset(qs, request)

            serializer = BookingSerializer(page, many=True)

            paginated = paginator.get_paginated_response(serializer.data).data
            paginated["stats"] = stats
            return Response(success_response(data=paginated, message="Bookings fetched"))
        except Exception as e:
            logger.error(f"BookingsView error: {e}")
            return Response(success_response(message="Something went wrong"), status=500)


class ConfirmBookingView(APIView):
    def post(self, request, booking_id):
        try:
            booking = Booking.objects.select_related("agent__owner").get(
                id=booking_id, agent__owner=request.user
            )
            confirmed = request.data.get("confirmed")
            if confirmed is None:
                from core.response_schemas import error_response
                return Response(error_response(message="'confirmed' field is required."), status=400)

            booking.is_confirmed = bool(confirmed)
            booking.confirmed_at = timezone.now() if bool(confirmed) else None
            booking.save(update_fields=["is_confirmed", "confirmed_at"])

            if bool(confirmed):
                from .tasks import send_booking_confirmation_email
                send_booking_confirmation_email(booking)

            logger.info(f"[BOOKING] {booking.id} confirmed={booking.is_confirmed}")
            return Response(success_response(
                message="Booking updated.",
                data={"id": str(booking.id), "is_confirmed": booking.is_confirmed},
            ))
        except Booking.DoesNotExist:
            from core.response_schemas import error_response
            return Response(error_response(message="Booking not found."), status=404)
        except Exception as e:
            logger.error(f"ConfirmBookingView error: {e}")
            from core.response_schemas import error_response
            return Response(error_response(message="Something went wrong."), status=500)


# ── Render views ───────────────────────────────────────────────────────────────

class VoiceDashboardRender(RenderAPIView):
    def get(self, request):
        return render(request, 'voice_dashboard.html')


class BookingsDashboardRender(RenderAPIView):
    def get(self, request):
        agents = Agent.objects.filter(owner=request.user).values("id", "agent_name")
        return render(request, "voice_bookings.html", {"agents": list(agents)})

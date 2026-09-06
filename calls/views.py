import uuid
from django.shortcuts import render
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import CallLog
from .serializers import CallLogSerializer, CallLogDetailSerializer
from core.auth_utils import RenderAPIView
from core.logger import logger
from agents.services import AgentMechanism
from agents.serializers import AgentListSerializer
from core.response_schemas import success_response, error_response
from rest_framework import status
from .services import CallLogService
from core.pagination import Pagination

class VoiceCallHistoryRender(RenderAPIView):
    def get(self, request):
        return render(request, 'voice_call_history.html')


class VoiceCallDetailRender(RenderAPIView):
    def get(self, request):
        pk = request.GET.get('pk', '')
        return render(request, 'voice_call_detail.html', {'pk': pk})



class DropDownsoptionsForCallHistory(APIView):
    def get(self, request):
        try:
            logger.info("Request received for call history dropdown options")
            agent_class = AgentMechanism()
            agents, message = agent_class.get_all_agents(request.user)
            if agents is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            data = {
                "agents": AgentListSerializer(agents, many=True).data,
                "sentiments": [
                    {"value": "positive", "label": "Positive"},
                    {"value": "negative", "label": "Negative"},
                    {"value": "neutral", "label": "Neutral"},
                ],
                "outcomes": [
                    {"value": value, "label": label}
                    for value, label in CallLog.OUTCOME_CHOICES
                ],
            }

            return Response(
                success_response(message="Call history dropdown options fetched successfully", data=data),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"DropDownsoptionsForCallHistory GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CallLogListView(APIView):
    pagination_class = Pagination

    def get(self, request):
        try:
            logger.info("Request received for CallLogListView")
            search = request.query_params.get("search", "").strip()
            agent_id = request.query_params.get("agent_id", "").strip()
            outcome = request.query_params.get("outcome", "").strip()
            sentiment = request.query_params.get("sentiment", "").strip()
            intent = request.query_params.get("intent", "").strip()

            calllog_class = CallLogService()
            calllogs, message = calllog_class.get_call_logs(
                request.user,
                search=search or None,
                agent_id=agent_id or None,
                outcome=outcome or None,
                sentiment=sentiment or None,
                intent=intent or None,
            )
            if calllogs is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            paginator  = self.pagination_class()
            paginated  = paginator.paginate_queryset(calllogs, request)
            serializer = CallLogSerializer(paginated, many=True)
            return paginator.get_paginated_response(
                success_response(message=message, data=serializer.data)
            )
        except Exception as e:
            logger.error(f"CallLogListView GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CallLogDetailView(APIView):
    def get(self, request, pk):
        try:
            logger.info(f"Request received for CallLogDetailView pk={pk}")
            calllog_class = CallLogService()
            calllog, message = calllog_class.get_call_log_detail(request.user, pk)
            if calllog is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)

            serializer = CallLogDetailSerializer(calllog)
            return Response(success_response(message=message, data=serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"CallLogDetailView GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CallLogBulkDeleteView(APIView):
    def delete(self, request):
        try:
            ids = request.data.get("ids", [])
            if not ids or not isinstance(ids, list):
                return Response(error_response(message="ids must be a non-empty list"), status=status.HTTP_400_BAD_REQUEST)

            valid_ids = []
            for raw_id in ids:
                try:
                    valid_ids.append(uuid.UUID(str(raw_id)))
                except (ValueError, AttributeError):
                    pass

            if not valid_ids:
                return Response(error_response(message="No valid IDs provided"), status=status.HTTP_400_BAD_REQUEST)

            calllog_class = CallLogService()
            deleted_count, message = calllog_class.bulk_delete_call_logs(request.user, valid_ids)
            if deleted_count is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(success_response(message=message, data={"deleted": deleted_count}), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"CallLogBulkDeleteView DELETE error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AgentCallStatsView(APIView):
    """KPI stats for a single agent — used by the agent detail page."""
    def get(self, request, agent_id):
        try:
            from agents.models import Agent, Booking
            try:
                agent = Agent.objects.get(id=agent_id, owner=request.user)
            except Agent.DoesNotExist:
                return Response(error_response(message="Agent not found"), status=status.HTTP_404_NOT_FOUND)

            calls = CallLog.objects.filter(agent=agent)
            total_calls     = calls.count()
            completed_calls = calls.filter(status="completed").count()
            booked_calls    = calls.filter(outcome="booked").count()
            booking_rate    = round((booked_calls / total_calls * 100), 1) if total_calls else 0
            avg_duration    = calls.aggregate(avg=Avg("duration_seconds"))["avg"] or 0
            avg_sentiment   = calls.exclude(sentiment_score=None).aggregate(avg=Avg("sentiment_score"))["avg"]
            total_bookings  = Booking.objects.filter(agent=agent).count()

            data = {
                "total_calls":    total_calls,
                "completed_calls": completed_calls,
                "booked_calls":   booked_calls,
                "booking_rate":   booking_rate,
                "avg_duration_seconds": round(avg_duration),
                "avg_sentiment":  round(avg_sentiment, 2) if avg_sentiment is not None else None,
                "total_bookings": total_bookings,
            }
            return Response(success_response(message="Agent stats fetched", data=data))
        except Exception as e:
            logger.error(f"AgentCallStatsView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyticsView(APIView):
    """Global analytics — KPIs, charts, agent comparison table (paginated)."""

    def get(self, request):
        try:
            from agents.models import Agent, Booking
            from django.db.models.functions import TruncDate, ExtractHour
            import math

            # --- date range filter ---
            range_days = int(request.query_params.get("days", 30))
            agent_id   = request.query_params.get("agent_id", "").strip()
            page       = int(request.query_params.get("page", 1))
            page_size  = int(request.query_params.get("page_size", 10))

            since = timezone.now() - timedelta(days=range_days)
            qs = CallLog.objects.filter(agent__owner=request.user, created_at__gte=since)
            if agent_id:
                qs = qs.filter(agent__id=agent_id)

            total_calls     = qs.count()
            completed_calls = qs.filter(status="completed").count()
            booked_calls    = qs.filter(outcome="booked").count()
            booking_rate    = round(booked_calls / total_calls * 100, 1) if total_calls else 0.0
            avg_duration    = qs.aggregate(avg=Avg("duration_seconds"))["avg"] or 0

            # --- call volume by day ---
            volume_qs = (
                qs.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            )
            call_volume = [{"date": str(r["day"]), "count": r["count"]} for r in volume_qs]

            # --- outcome breakdown ---
            outcome_qs = qs.values("outcome").annotate(count=Count("id")).order_by("-count")
            outcome_breakdown = [{"outcome": r["outcome"], "count": r["count"]} for r in outcome_qs]

            # --- booking rate trend (weekly buckets inside the range) ---
            from django.db.models.functions import TruncWeek
            trend_qs = (
                qs.annotate(week=TruncWeek("created_at"))
                .values("week")
                .annotate(
                    total=Count("id"),
                    booked=Count("id", filter=Q(outcome="booked")),
                )
                .order_by("week")
            )
            booking_trend = [
                {
                    "week": str(r["week"].date()),
                    "rate": round(r["booked"] / r["total"] * 100, 1) if r["total"] else 0.0,
                }
                for r in trend_qs
            ]

            # --- top call intents (outcome as proxy) ---
            intent_qs = qs.values("outcome").annotate(count=Count("id")).order_by("-count")
            top_intents = [{"intent": r["outcome"], "count": r["count"]} for r in intent_qs]

            # --- hourly heatmap ---
            hour_qs = (
                qs.annotate(hour=ExtractHour("created_at"))
                .values("hour")
                .annotate(count=Count("id"))
                .order_by("hour")
            )
            hour_map = {r["hour"]: r["count"] for r in hour_qs}
            hourly_heatmap = [{"hour": h, "count": hour_map.get(h, 0)} for h in range(24)]

            # --- agent performance table (paginated) ---
            agents_qs = Agent.objects.filter(owner=request.user).order_by("-created_at")[:3]
            agent_total = agents_qs.count()
            agents_page = agents_qs[(page - 1) * page_size : page * page_size]

            agent_rows = []
            for agent in agents_page:
                agent_calls = qs.filter(agent=agent)
                a_total    = agent_calls.count()
                a_booked   = agent_calls.filter(outcome="booked").count()
                a_handoff  = agent_calls.filter(was_transferred=True).count()
                a_dur      = agent_calls.aggregate(avg=Avg("duration_seconds"))["avg"] or 0
                a_sent     = agent_calls.exclude(sentiment_score=None).aggregate(avg=Avg("sentiment_score"))["avg"]
                agent_rows.append({
                    "id":           str(agent.id),
                    "agent_name":   agent.agent_name,
                    "status":       agent.status,
                    "total_calls":  a_total,
                    "booking_rate": round(a_booked / a_total * 100, 1) if a_total else 0.0,
                    "avg_duration": round(a_dur),
                    "avg_sentiment": round(a_sent, 2) if a_sent is not None else None,
                    "handoff_rate": round(a_handoff / a_total * 100, 1) if a_total else 0.0,
                })

            agent_pagination = {
                "total": agent_total,
                "page": page,
                "page_size": page_size,
                "total_pages": math.ceil(agent_total / page_size) if page_size else 1,
            }

            data = {
                "kpis": {
                    "total_calls":       total_calls,
                    "completed_calls":   completed_calls,
                    "booked_calls":      booked_calls,
                    "booking_rate":      booking_rate,
                    "avg_duration_seconds": round(avg_duration),
                },
                "call_volume":     call_volume,
                "outcome_breakdown": outcome_breakdown,
                "booking_trend":   booking_trend,
                "top_intents":     top_intents,
                "hourly_heatmap":  hourly_heatmap,
                "agent_performance": {
                    "pagination": agent_pagination,
                    "results":    agent_rows,
                },
            }
            return Response(success_response(message="Analytics fetched", data=data))
        except Exception as e:
            logger.error(f"AnalyticsView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DemoTokenView(APIView):
    """Demo agent metadata only — Twilio voice tokens removed."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from agents.models import Agent
            agent = Agent.objects.filter(is_demo=True, status="live").first()
            agent_id = str(agent.id) if agent else None

            agent_info = None
            if agent:
                tools = list(
                    agent.user_tools.select_related("user_tool")
                    .filter(is_active=True, user_tool__is_active=True)
                    .values_list("user_tool__name", flat=True)
                )
                agent_info = {
                    "name": agent.agent_name,
                    "description": agent.system_prompt[:200] if agent.system_prompt else "",
                    "tools": list(tools),
                }

            return Response({
                "token": None,
                "agent_id": agent_id,
                "agent_info": agent_info,
                "message": "Twilio FastAPI voice runtime removed. Use Retell for live calls.",
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

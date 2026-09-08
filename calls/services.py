from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import CallLog


class CallLogService:

    def _owned_qs(self, user):
        """Calls owned via agent. Orphans excluded to avoid cross-tenant leaks."""
        return (
            CallLog.objects
            .select_related("agent")
            .filter(agent__owner=user)
            .order_by("-created_at")
        )

    def get_call_logs(
        self,
        user,
        search=None,
        agent_id=None,
        sentiment=None,
        intent=None,
        days=None,
    ):
        try:
            call_logs = self._owned_qs(user)

            if days:
                try:
                    days_int = int(days)
                    if days_int > 0:
                        since = timezone.now() - timedelta(days=days_int)
                        call_logs = call_logs.filter(
                            Q(created_at__gte=since) | Q(started_at__gte=since)
                        )
                except (TypeError, ValueError):
                    pass

            if search:
                call_logs = call_logs.filter(
                    Q(caller_phone__icontains=search)
                    | Q(twilio_call_sid__icontains=search)
                    | Q(agent__agent_name__icontains=search)
                )

            if agent_id:
                call_logs = call_logs.filter(agent_id=agent_id)

            if intent:
                call_logs = call_logs.filter(reason__icontains=intent)

            if sentiment == "positive":
                call_logs = call_logs.filter(sentiment_score__iexact="positive")
            elif sentiment == "negative":
                call_logs = call_logs.filter(sentiment_score__iexact="negative")
            elif sentiment == "neutral":
                # Explicit neutral + legacy zero floats only (not blank/unanalyzed)
                call_logs = call_logs.filter(
                    Q(sentiment_score__iexact="neutral")
                    | Q(sentiment_score="0.0")
                    | Q(sentiment_score="0")
                )

            return call_logs, "Call logs fetched successfully"
        except Exception as e:
            return None, f"Error fetching call logs: {e}"

    def bulk_delete_call_logs(self, user, ids):
        try:
            deleted_count, _ = (
                self._owned_qs(user)
                .filter(id__in=ids)
                .delete()
            )
            return deleted_count, f"call(s) deleted successfully"
        except Exception as e:
            return None, f"Error deleting call logs: {e}"

    def get_call_log_detail(self, user, call_id):
        try:
            call_log = (
                self._owned_qs(user)
                .prefetch_related("transcripts")
                .get(id=call_id)
            )
            return call_log, "Call log fetched successfully"
        except CallLog.DoesNotExist:
            return None, "Call log not found"
        except Exception as e:
            return None, f"Error fetching call log: {e}"

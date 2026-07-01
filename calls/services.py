from .models import CallLog, CallTranscript
from django.db.models import Q


class CallLogService:

    def get_call_logs(self, user, search=None, agent_id=None, outcome=None, sentiment=None, intent=None):
        try:
            call_logs = (
                CallLog.objects
                .select_related("agent")
                .filter(agent__owner=user)
                .order_by("-created_at")
            )

            if search:
                call_logs = call_logs.filter(
                    Q(caller_phone__icontains=search)
                    | Q(twilio_call_sid__icontains=search)
                    | Q(agent__agent_name__icontains=search)
                )

            if agent_id:
                call_logs = call_logs.filter(agent_id=agent_id)

            if outcome:
                call_logs = call_logs.filter(outcome=outcome)

            if intent:
                call_logs = call_logs.filter(reason__icontains=intent)

            if sentiment == "positive":
                call_logs = call_logs.filter(sentiment_score__gt=0.05)
            elif sentiment == "negative":
                call_logs = call_logs.filter(sentiment_score__lt=-0.05)
            elif sentiment == "neutral":
                call_logs = call_logs.filter(
                    Q(sentiment_score__isnull=True)
                    | Q(sentiment_score__gte=-0.05, sentiment_score__lte=0.05)
                )

            return call_logs, "Call logs fetched successfully"
        except Exception as e:
            return None, f"Error fetching call logs: {e}"

    def bulk_delete_call_logs(self, user, ids):
        try:
            deleted_count, _ = (
                CallLog.objects
                .filter(id__in=ids, agent__owner=user)
                .delete()
            )
            return deleted_count, f"call(s) deleted successfully"
        except Exception as e:
            return None, f"Error deleting call logs: {e}"

    def get_call_log_detail(self, user, call_id):
        try:
            call_log = (
                CallLog.objects
                .select_related("agent")
                .prefetch_related("transcripts", "agent__tools__tool")
                .get(id=call_id, agent__owner=user)
            )
            return call_log, "Call log fetched successfully"
        except CallLog.DoesNotExist:
            return None, "Call log not found"
        except Exception as e:
            return None, f"Error fetching call log: {e}"

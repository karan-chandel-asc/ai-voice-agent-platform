from django.db import models


class ProjectVisit(models.Model):
    """Record of someone opening the Deskline public project (outreach tracking)."""

    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    country = models.CharField(max_length=100, blank=True, default="", db_index=True)
    country_code = models.CharField(max_length=8, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="/")
    referrer = models.CharField(max_length=500, blank=True, default="")
    user_agent = models.CharField(max_length=500, blank=True, default="")
    visited_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-visited_at"]
        indexes = [
            models.Index(fields=["visited_at", "country"]),
            models.Index(fields=["ip_address", "visited_at"]),
        ]

    def __str__(self):
        where = self.country or "Unknown"
        return f"{self.ip_address or '?'} · {where} · {self.path} · {self.visited_at:%Y-%m-%d %H:%M}"

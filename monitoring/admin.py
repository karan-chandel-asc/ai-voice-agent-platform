from django.contrib import admin

from .models import ProjectVisit


@admin.register(ProjectVisit)
class ProjectVisitAdmin(admin.ModelAdmin):
    list_display = ("visited_at", "country", "city", "path", "ip_address")
    list_filter = ("country", "path")
    search_fields = ("ip_address", "country", "city", "path", "referrer")
    readonly_fields = (
        "ip_address",
        "country",
        "country_code",
        "city",
        "path",
        "referrer",
        "user_agent",
        "visited_at",
    )
    ordering = ("-visited_at",)

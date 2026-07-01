from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as page_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("",       page_views.home, name="home"),
    # API
    path("api/auth/", include("accounts.urls")),
    path("api/agents/", include("agents.urls")),
    path("api/calls/", include("calls.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/integrations/", include("integrations.urls")),
    path("api/knowledge/", include("knowledge.urls")),
    path("api/monitoring/", include("monitoring.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.urls import path
from .views import DashboardStatsView, VoiceDashboardRender, BookingsView, BookingsDashboardRender, ConfirmBookingView

urlpatterns = [
    path("voice-dashboard/",              VoiceDashboardRender.as_view(),   name="voice-dashboard"),
    path("stats/",                        DashboardStatsView.as_view(),      name="dashboard-stats"),
    path("bookings/",                     BookingsDashboardRender.as_view(), name="voice-bookings"),
    path("bookings/data/",                BookingsView.as_view(),            name="bookings-data"),
    path("bookings/<uuid:booking_id>/confirm/", ConfirmBookingView.as_view(), name="booking-confirm"),
]


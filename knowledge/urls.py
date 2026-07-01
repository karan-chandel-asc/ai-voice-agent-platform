from django.urls import path
from .views import (
    VoiceKnowledgeBaseRender,
    AgentListForKBView,
    DocumentListView,
    DocumentUploadView,
    DocumentDeleteView,
)

urlpatterns = [
    path("voice-knowledge-base/",         VoiceKnowledgeBaseRender.as_view(), name="voice-knowledge-base"),
    path("agents/",                        AgentListForKBView.as_view(),       name="kb-agents"),
    path("documents/",                     DocumentListView.as_view(),         name="kb-documents"),
    path("documents/upload/",             DocumentUploadView.as_view(),       name="kb-upload"),
    path("documents/<str:doc_id>/delete/", DocumentDeleteView.as_view(),      name="kb-delete"),
]

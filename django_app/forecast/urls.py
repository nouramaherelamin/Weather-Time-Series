from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("insights/", views.insights, name="insights"),
    path("batch/", views.batch, name="batch"),
    path("batch/sample.csv", views.batch_sample, name="batch_sample"),
    path("history/export.csv", views.history_export, name="history_export"),
    path("history/clear/", views.history_clear, name="history_clear"),
    path("about/", views.about, name="about"),
    path("api/", views.api_docs, name="api_docs"),
    path("api/swagger/", views.swagger, name="swagger"),
    path("api/openapi.json", views.openapi, name="openapi"),
    path("api/predict/", views.api_predict, name="api_predict"),
    path("api/latest/", views.api_latest, name="api_latest"),
    path("api/batch/", views.api_batch, name="api_batch"),
    path("api/models/", views.api_models, name="api_models"),
    path("api/health/", views.api_health, name="api_health"),
]

from django.urls import path
from . import views

urlpatterns = [
    # The edge node will send data to this specific path
    path('ingest/', views.ingest_data, name='ingest_data'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
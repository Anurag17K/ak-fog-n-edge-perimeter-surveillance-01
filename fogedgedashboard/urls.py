from django.urls import path
from . import views

urlpatterns = [
    # The edge node will send data to this specific path
    path('ingest/', views.ingest_data, name='ingest_data'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('toggle-override/', views.toggle_override, name='toggle_override'),
    path('get-dashboard-data/', views.api_get_dashboard_data, name='get_dashboard_data'),
    path('get-session-data/', views.api_get_session_data, name='get_session_data'),
]
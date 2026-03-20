import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SecurityAlert

@csrf_exempt
def ingest_data(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            
            # Only save actual threats to the database to save space
            if payload.get("alert") != "None":
                raw_data = payload.get("raw_data_sample", {})
                
                # Save to database
                SecurityAlert.objects.create(
                    alert_type=payload.get("alert"),
                    status=payload.get("status"),
                    rf_signal=raw_data.get("rf_signal_strength_dbm", 0),
                    acoustic_freq=raw_data.get("acoustic_frequency_hz", 0),
                    seismic_vib=raw_data.get("seismic_vibration_g", 0),
                    object_mass=raw_data.get("thermal_object_mass_kg", 0)
                )
                print(f"💾 SAVED TO DB: {payload.get('alert')}")

            return JsonResponse({"message": "Data ingested successfully", "status": 200})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    return JsonResponse({"error": "Only POST methods are allowed"}, status=405)

# --- NEW DASHBOARD VIEW ---
def dashboard_view(request):
    # 1. Get the latest 15 alerts for the table and charts
    latest_alerts = SecurityAlert.objects.all().order_by('-timestamp')[:15]
    
    # We need to reverse them so the line chart reads left-to-right (oldest to newest)
    chart_alerts = list(reversed(latest_alerts))
    
    # 2. Extract data for the Line Chart
    time_labels = [alert.timestamp.strftime("%H:%M:%S") for alert in chart_alerts]
    rf_data = [alert.rf_signal for alert in chart_alerts]
    seismic_data = [alert.seismic_vib for alert in chart_alerts]

    # 3. Count alerts for the Doughnut chart
    drone_count = SecurityAlert.objects.filter(alert_type="Airspace Drone Breach").count()
    trespass_count = SecurityAlert.objects.filter(alert_type="Ground Trespass").count()
    vehicle_count = SecurityAlert.objects.filter(alert_type="Unauthorized Vehicle Approach").count()
    fence_count = SecurityAlert.objects.filter(alert_type="Fence Tampering / Cutting").count()
    
    # Total threats saved to cloud
    total_threats = SecurityAlert.objects.count()
    # Mocking the filtered false alarms (Assuming 96% of edge data is filtered out)
    false_alarms_filtered = total_threats * 24 

    context = {
        'alerts': latest_alerts,
        'doughnut_data': [drone_count, trespass_count, vehicle_count, fence_count],
        'time_labels': time_labels,
        'rf_data': rf_data,
        'seismic_data': seismic_data,
        'total_threats': total_threats,
        'false_alarms': false_alarms_filtered
    }
    return render(request, 'dashboard.html', context)
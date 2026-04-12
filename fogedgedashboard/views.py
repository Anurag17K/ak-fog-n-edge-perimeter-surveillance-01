import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SecurityAlert
from django.utils import timezone
import boto3
from django.conf import settings

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
        'false_alarms': false_alarms_filtered,
        'last_updated': timezone.now()
    }
    return render(request, 'dashboard.html', context)

@csrf_exempt
def toggle_override(request):
    """Sends a Command & Control message down to the local Fog Node via AWS IoT."""
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            # Expecting a payload like: {"system_active": false}
            is_active = payload.get("system_active", True)
            
            # Create a message payload for the Fog Node
            command_message = json.dumps({"system_active": is_active})
            
            # Initialize the AWS IoT Data client
            # (boto3 will automatically use your local AWS CLI credentials for now)
            iot_client = boto3.client('iot-data', region_name='us-east-1') # Update region if needed
            
            # Publish the command to a specific control topic
            iot_client.publish(
                topic='perimeter/commands/override',
                qos=1,
                payload=command_message
            )
            
            status_text = "ACTIVATED" if is_active else "DEACTIVATED"
            print(f"📡 CLOUD COMMAND SENT: System {status_text}")
            
            return JsonResponse({"message": "Command transmitted successfully", "status": 200})
            
        except Exception as e:
            print(f"Error sending command: {e}")
            return JsonResponse({"error": str(e)}, status=500)
            
    return JsonResponse({"error": "Invalid request"}, status=400)
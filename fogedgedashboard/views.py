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
    """
    Handles both the AWS IoT HTTPS Destination confirmation handshake 
    and the ingestion of real-time threat data from the Fog Node.
    """
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            
            # --- 1. AWS IoT HTTPS CONFIRMATION HANDSHAKE ---
            if 'confirmationToken' in payload:
                print(f"[SYSTEM] AWS IoT Handshake Received. Token: {payload['confirmationToken']}")
                return JsonResponse({"status": "confirmed"}, status=200)

            # --- 2. THREAT DATA INGESTION LOGIC ---
            alert_type = payload.get("alert")
            
            if alert_type and alert_type != "None":
                raw_data = payload.get("raw_data_sample", {})
                
                SecurityAlert.objects.create(
                    alert_type=alert_type,
                    status=payload.get("status", "No Status Provided"),
                    rf_signal=raw_data.get("rf_signal_strength_dbm", 0),
                    acoustic_freq=raw_data.get("acoustic_frequency_hz", 0),
                    seismic_vib=raw_data.get("seismic_vibration_g", 0),
                    object_mass=raw_data.get("thermal_object_mass_kg", 0)
                )
                print(f"[DATABASE] Saved record: {alert_type}")

            return JsonResponse({"message": "Data ingested successfully", "status": 200})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)
        except Exception as e:
            print(f"[ERROR] Ingestion Error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only POST methods are allowed"}, status=405)

def dashboard_view(request):
    latest_alerts = SecurityAlert.objects.all().order_by('-timestamp')[:15]
    chart_alerts = list(reversed(latest_alerts))
    
    time_labels = [alert.timestamp.strftime("%H:%M:%S") for alert in chart_alerts]
    rf_data = [alert.rf_signal for alert in chart_alerts]
    seismic_data = [alert.seismic_vib for alert in chart_alerts]
    
    # NEW: Extract the alert type for the line chart filtering
    alert_types_data = [alert.alert_type for alert in chart_alerts]

    drone_count = SecurityAlert.objects.filter(alert_type="Airspace Drone Breach").count()
    trespass_count = SecurityAlert.objects.filter(alert_type="Ground Trespass").count()
    vehicle_count = SecurityAlert.objects.filter(alert_type="Unauthorized Vehicle Approach").count()
    fence_count = SecurityAlert.objects.filter(alert_type="Fence Tampering / Cutting").count()
    
    total_threats = SecurityAlert.objects.count()
    false_alarms_filtered = total_threats * 24 

    context = {
        'alerts': latest_alerts,
        'doughnut_data': [drone_count, trespass_count, vehicle_count, fence_count],
        'time_labels': time_labels,
        'rf_data': rf_data,
        'seismic_data': seismic_data,
        'alert_types_data': alert_types_data, # NEW: Add this to the context
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
            is_active = payload.get("system_active", True)
            
            command_message = json.dumps({"system_active": is_active})
            iot_client = boto3.client('iot-data', region_name='us-east-1')
            
            iot_client.publish(
                topic='perimeter/commands/override',
                qos=1,
                payload=command_message
            )
            
            status_text = "ACTIVATED" if is_active else "DEACTIVATED"
            print(f"[COMMAND] Cloud command transmitted: System {status_text}")
            
            return JsonResponse({"message": "Command transmitted successfully", "status": 200})
            
        except Exception as e:
            print(f"[ERROR] Error sending command: {e}")
            return JsonResponse({"error": str(e)}, status=500)
            
    return JsonResponse({"error": "Invalid request"}, status=400)
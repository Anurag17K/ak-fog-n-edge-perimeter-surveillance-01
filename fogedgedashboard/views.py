import json
import datetime
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
            
            if 'confirmationToken' in payload:
                print(f"[SYSTEM] AWS IoT Handshake Received. Token: {payload['confirmationToken']}")
                return JsonResponse({"status": "confirmed"}, status=200)

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

def get_dashboard_metrics():
    """Helper function to gather all metrics so we don't duplicate code."""
    today = timezone.now()
    
    # 1. WEEK DATA
    week_labels = [(today - datetime.timedelta(days=i)).strftime("%b %d") for i in range(6, -1, -1)]
    week_data = {'Drones': [0]*7, 'Vehicles': [0]*7, 'Trespassers': [0]*7, 'Fence': [0]*7}
    week_alerts = SecurityAlert.objects.filter(timestamp__gte=today - datetime.timedelta(days=7))
    for a in week_alerts:
        idx = 6 - (today.date() - a.timestamp.date()).days
        if 0 <= idx < 7:
            if "Drone" in a.alert_type: week_data['Drones'][idx] += 1
            elif "Vehicle" in a.alert_type: week_data['Vehicles'][idx] += 1
            elif "Trespass" in a.alert_type: week_data['Trespassers'][idx] += 1
            elif "Fence" in a.alert_type: week_data['Fence'][idx] += 1

    # 2. MONTH DATA
    month_labels = [(today - datetime.timedelta(days=i)).strftime("%b %d") for i in range(29, -1, -1)]
    month_data = {'Drones': [0]*30, 'Vehicles': [0]*30, 'Trespassers': [0]*30, 'Fence': [0]*30}
    month_alerts = SecurityAlert.objects.filter(timestamp__gte=today - datetime.timedelta(days=30))
    for a in month_alerts:
        idx = 29 - (today.date() - a.timestamp.date()).days
        if 0 <= idx < 30:
            if "Drone" in a.alert_type: month_data['Drones'][idx] += 1
            elif "Vehicle" in a.alert_type: month_data['Vehicles'][idx] += 1
            elif "Trespass" in a.alert_type: month_data['Trespassers'][idx] += 1
            elif "Fence" in a.alert_type: month_data['Fence'][idx] += 1

    # 3. YEAR DATA
    year_labels = []
    year_data = {'Drones': [0]*12, 'Vehicles': [0]*12, 'Trespassers': [0]*12, 'Fence': [0]*12}
    for i in range(11, -1, -1):
        target_month = (today.month - i - 1) % 12 + 1
        target_year = today.year + ((today.month - i - 1) // 12)
        year_labels.append(datetime.date(target_year, target_month, 1).strftime("%b %Y"))

    year_alerts = SecurityAlert.objects.filter(timestamp__gte=today - datetime.timedelta(days=365))
    for a in year_alerts:
        month_diff = (today.year - a.timestamp.year) * 12 + today.month - a.timestamp.month
        idx = 11 - month_diff
        if 0 <= idx < 12:
            if "Drone" in a.alert_type: year_data['Drones'][idx] += 1
            elif "Vehicle" in a.alert_type: year_data['Vehicles'][idx] += 1
            elif "Trespass" in a.alert_type: year_data['Trespassers'][idx] += 1
            elif "Fence" in a.alert_type: year_data['Fence'][idx] += 1

    trend_payload = {
        "week": {"labels": week_labels, "data": week_data},
        "month": {"labels": month_labels, "data": month_data},
        "year": {"labels": year_labels, "data": year_data}
    }

    # KPIs and Table Data
    latest_alerts = SecurityAlert.objects.all().order_by('-timestamp')[:15]
    
    # Pre-format alerts for JSON (Django models aren't JSON serializable by default)
    alerts_list = [{
        "timestamp": a.timestamp.strftime("%H:%M:%S"),
        "alert_type": a.alert_type,
        "status": a.status,
        "rf_signal": a.rf_signal,
        "seismic_vib": a.seismic_vib
    } for a in latest_alerts]

    total_threats = SecurityAlert.objects.count()

    return {
        'alerts_queryset': latest_alerts, # Used by the initial HTML render
        'alerts_json': alerts_list,       # Used by the AJAX poll
        'doughnut_data': [
            SecurityAlert.objects.filter(alert_type__icontains="Drone").count(),
            SecurityAlert.objects.filter(alert_type__icontains="Trespass").count(),
            SecurityAlert.objects.filter(alert_type__icontains="Vehicle").count(),
            SecurityAlert.objects.filter(alert_type__icontains="Fence").count()
        ],
        'trend_payload': trend_payload,
        'total_threats': total_threats,
        'false_alarms': total_threats * 24,
        'last_updated': today.strftime("%H:%M:%S")
    }

# ==========================================
# VIEW 1: Renders the initial HTML page
# ==========================================
def dashboard_view(request):
    data = get_dashboard_metrics()
    context = {
        'alerts': data['alerts_queryset'],
        'doughnut_data': data['doughnut_data'],
        'trend_payload': json.dumps(data['trend_payload']),
        'total_threats': data['total_threats'],
        'false_alarms': data['false_alarms'],
        'last_updated': data['last_updated']
    }
    return render(request, 'dashboard.html', context)

# ==========================================
# VIEW 2: Provides fresh JSON to the frontend every 5 seconds
# ==========================================
def api_get_dashboard_data(request):
    data = get_dashboard_metrics()
    return JsonResponse({
        'alerts': data['alerts_json'],
        'doughnut_data': data['doughnut_data'],
        'trend_payload': data['trend_payload'],
        'total_threats': data['total_threats'],
        'false_alarms': data['false_alarms'],
        'last_updated': data['last_updated']
    })

@csrf_exempt
def toggle_override(request):
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

@csrf_exempt
def api_get_session_data(request):
    """Feeds the live sub-dashboard with data strictly after a given timestamp."""
    since_ts = request.GET.get('since')
    if not since_ts:
        return JsonResponse({"error": "Missing timestamp"}, status=400)
        
    try:
        # Convert the JavaScript timestamp to a UTC aware datetime
        dt = datetime.datetime.fromtimestamp(int(since_ts) / 1000.0, tz=datetime.timezone.utc)
        
        # CRITICAL FIX: If your Django settings use naive datetimes (USE_TZ=False), 
        # strip the timezone info so it doesn't crash the database query.
        if not getattr(settings, 'USE_TZ', True):
            dt = dt.replace(tzinfo=None)
            
    except Exception as e:
        print(f"[ERROR] Session Time Conversion: {e}")
        return JsonResponse({"error": "Invalid timestamp"}, status=400)

    # Filter alerts that happened AFTER the button was clicked
    session_alerts = SecurityAlert.objects.filter(timestamp__gte=dt).order_by('-timestamp')
    
    alerts_json = [{
        "timestamp": a.timestamp.strftime("%H:%M:%S"),
        "alert_type": a.alert_type,
        "status": a.status,
        "rf_signal": a.rf_signal,
        "seismic_vib": a.seismic_vib
    } for a in session_alerts[:30]] # Limit to last 30 for snappy UI

    return JsonResponse({
        'total_threats': session_alerts.count(),
        'drones': session_alerts.filter(alert_type__icontains="Drone").count(),
        'vehicles': session_alerts.filter(alert_type__icontains="Vehicle").count(),
        'trespass': session_alerts.filter(alert_type__icontains="Trespass").count(),
        'fence': session_alerts.filter(alert_type__icontains="Fence").count(),
        'alerts': alerts_json
    })
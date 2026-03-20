import time
import random
import requests

CLOUD_URL = "http://127.0.0.1:8080/api/ingest/"

def generate_virtual_sensors():
    """Generates dummy data, now with 4 distinct threat profiles."""
    trigger = random.randint(1, 100) # Expanded the pool to 20
    print(trigger)
    
    if trigger == 1: 
        # THREAT 1: DRONE (Strong RF, High Pitch, Low Mass)
        rf = random.uniform(-40.0, -20.0)
        acoustic = random.randint(4000, 6000)
        seismic = random.uniform(0.0, 0.1)
        mass = random.uniform(1.0, 4.0)
    elif trigger == 2: 
        # THREAT 2: TRESPASSER (Footsteps, Human Mass)
        rf = random.uniform(-90.0, -80.0)
        acoustic = random.randint(50, 200)
        seismic = random.uniform(0.4, 0.8)
        mass = random.uniform(60.0, 90.0)
    elif trigger == 3:
        # THREAT 3: UNAUTHORIZED VEHICLE (Heavy Mass, Low Engine Rumble)
        rf = random.uniform(-100.0, -85.0)
        acoustic = random.randint(80, 120) 
        seismic = random.uniform(1.5, 3.0) # Heavy ground vibration
        mass = random.uniform(1500.0, 3000.0) # Weight of a car/truck
    elif trigger == 4:
        # THREAT 4: FENCE TAMPERING (Metal grinding acoustic, fence vibration, low mass)
        rf = random.uniform(-100.0, -85.0)
        acoustic = random.randint(2000, 3000) # Screeching metal
        seismic = random.uniform(0.2, 0.5)
        mass = random.uniform(0.0, 5.0) # No heavy body detected
    else: 
        # NORMAL BASELINE (Birds, wind, distant traffic)
        rf = random.uniform(-100.0, -85.0)
        acoustic = random.randint(30, 300)
        seismic = random.uniform(0.0, 0.2)
        mass = random.choice([2.0, 75.0, 500.0])

    return {
        "rf_signal_strength_dbm": round(rf, 2),
        "acoustic_frequency_hz": acoustic,
        "seismic_vibration_g": round(seismic, 2),
        "thermal_object_mass_kg": round(mass, 2)
    }

def process_at_edge(sensors):
    """The Fog Node brain, now handling 4 different scenarios."""
    payload = {"alert": "None", "status": "All Clear", "raw_data_sample": sensors}
    
    # 1. Drone Logic
    if sensors["rf_signal_strength_dbm"] > -50 and sensors["acoustic_frequency_hz"] > 4000 and sensors["thermal_object_mass_kg"] < 5.0:
        print("\n>> EDGE ACTION: Drone Detected. Activating 2.4GHz Jammer.")
        payload["alert"] = "Airspace Drone Breach"
        payload["status"] = "Local Jammer Active"
        return payload
        
    # 2. Trespasser Logic
    if 0.4 <= sensors["seismic_vibration_g"] <= 1.0 and 60.0 <= sensors["thermal_object_mass_kg"] <= 90.0:
        print("\n>> EDGE ACTION: Human Footsteps. Activating Sector Floodlights.")
        payload["alert"] = "Ground Trespass"
        payload["status"] = "Perimeter Lockdown Engaged"
        return payload

    # 3. Vehicle Logic
    if sensors["seismic_vibration_g"] > 1.5 and sensors["thermal_object_mass_kg"] > 1000.0:
        print("\n>> EDGE ACTION: Heavy Vehicle Detected. Deploying Hydraulic Bollards.")
        payload["alert"] = "Unauthorized Vehicle Approach"
        payload["status"] = "Hydraulic Bollards Raised"
        return payload

    # 4. Fence Tampering Logic
    if 2000 <= sensors["acoustic_frequency_hz"] <= 3500 and sensors["thermal_object_mass_kg"] < 10.0:
        print("\n>> EDGE ACTION: Metal Grinding Detected. Sounding Local Warning Siren.")
        payload["alert"] = "Fence Tampering / Cutting"
        payload["status"] = "Warning Siren Activated"
        return payload

    # 5. False Alarm (Ignore)
    print(".", end="", flush=True) 
    return payload

def run_fog_node():
    print("Starting Upgraded Threat Management Edge Node...")
    while True:
        sensors = generate_virtual_sensors()
        payload = process_at_edge(sensors)
        
        if payload["alert"] != "None":
            try:
                response = requests.post(CLOUD_URL, json=payload)
                if response.status_code == 200:
                    print("   -> ☁️ [SUCCESS] Alert dispatched to Django!")
            except requests.exceptions.ConnectionError:
                print("\n[ERROR] Could not connect to Django Backend. Is the server running?")
        
        time.sleep(2)

if __name__ == "__main__":
    run_fog_node()
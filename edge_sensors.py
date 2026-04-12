import time
import json
import random
import socket

# Setup a local UDP network (Simulating a local perimeter wire)
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("📡 Edge Sensors Active. Blasting raw telemetry over local network...")

while True:
    # Simulating the physical environment
    rf_dbm = random.uniform(-100.0, -20.0)
    vibration_g = random.uniform(0.0, 3.0)
    
    payload = {
        "rf_dbm": round(rf_dbm, 2),
        "vibration_g": round(vibration_g, 2)
    }
    
    # Send the raw data to the Fog Brain via local UDP
    sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))
    print(f"[{time.strftime('%H:%M:%S')}] Raw Data Sent -> RF: {payload['rf_dbm']} | Vib: {payload['vibration_g']}")
    
    time.sleep(2)
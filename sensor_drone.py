import time, json, random, socket

UDP_IP, UDP_PORT = "127.0.0.1", 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("[EDGE] Airspace Radar Active. Scanning for Drones...")

while True:
    trigger = random.randint(1, 10) # 10% chance of threat
    if trigger == 1:
        rf = random.uniform(-40.0, -20.0)
        acoustic = random.randint(4000, 6000)
        seismic = random.uniform(0.0, 0.1)
        mass = random.uniform(1.0, 4.0)
        print("detected")
    else:
        rf, acoustic, seismic, mass = random.uniform(-100.0, -85.0), random.randint(30, 300), random.uniform(0.0, 0.2), 2.0

    payload = {"rf_dbm": round(rf, 2), "acoustic_hz": acoustic, "seismic_g": round(seismic, 2), "mass_kg": round(mass, 2)}
    sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))
    time.sleep(3)
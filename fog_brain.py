import time
import json
import socket
from awscrt import mqtt, io
from awsiot import mqtt_connection_builder

# --- AWS IoT Core Configuration ---
AWS_ENDPOINT = "ab9f3ng515b54-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "local-fog-node-fne-01"
PUBLISH_TOPIC = "perimeter/alerts/cloud"
COMMAND_TOPIC = "perimeter/commands/override"

CERT_PATH = "certs/711cb158c69c1d18ce10d3d3354fa4063498bd29f311693add4e959eea59c4b8-certificate.pem.crt"
KEY_PATH = "certs/711cb158c69c1d18ce10d3d3354fa4063498bd29f311693add4e959eea59c4b8-private.pem.key"
CA_PATH = "certs/AmazonRootCA1.pem"

# --- LOCAL NETWORK SETUP ---
# Listen for specialized Edge Sensors (sensor_drone, sensor_vehicle, etc.)
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind((UDP_IP, UDP_PORT))

# Crucial: Set a timeout so the while loop doesn't hang forever waiting for sensors.
# This allows the heartbeat timer to keep ticking even if sensors go offline.
udp_sock.settimeout(1.0) 

# Global System State
system_is_active = True

def on_command_received(topic, payload, dup, qos, retain, **kwargs):
    """Callback triggered when a command arrives from the Django Dashboard."""
    global system_is_active
    try:
        message = json.loads(payload.decode('utf-8'))
        if "system_active" in message:
            system_is_active = message["system_active"]
            if system_is_active:
                print("\n[CLOUD COMMAND] Defenses Reactivated! Resuming perimeter scans...")
            else:
                print("\n[CLOUD COMMAND] Defenses Deactivated! System entering standby...")
    except Exception as e:
        print(f"Error parsing command payload: {e}")

def connect_to_aws():
    """Builds secure MQTT connection using mutual TLS."""
    print("Building secure MQTT connection to AWS IoT Core...")
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    connection = mqtt_connection_builder.mtls_from_path(
        endpoint=AWS_ENDPOINT,
        cert_filepath=CERT_PATH,
        pri_key_filepath=KEY_PATH,
        client_bootstrap=client_bootstrap,
        ca_filepath=CA_PATH,
        client_id=CLIENT_ID,
        clean_session=False,
        keep_alive_secs=60
    )
    
    # Block until connection is established
    connection.connect().result()
    print("AWS Connection Established!")
    
    # Subscribe to the command topic for bidirectional control
    print(f"Subscribing to: {COMMAND_TOPIC}")
    connection.subscribe(
        topic=COMMAND_TOPIC,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_command_received
    )[0].result()
    
    return connection

def run_fog_logic(aws_connection):
    """Aggregates raw data from multiple edge sensors and filters for threats."""
    print("\nFOG BRAIN ACTIVE. Listening for specialized Edge Sensors on Port 5005...")
    global system_is_active
    
    # --- METRICS TRACKING ---
    dropped_alarms = 0
    last_heartbeat_time = time.time()
    HEARTBEAT_INTERVAL = 60  # Send false alarm counts to cloud every 60 seconds
    
    while True:
        # --- 1. HEARTBEAT CHECK ---
        current_time = time.time()
        if current_time - last_heartbeat_time >= HEARTBEAT_INTERVAL:
            if dropped_alarms > 0:
                heartbeat_payload = {
                    "payload_type": "heartbeat",
                    "dropped_alarms": dropped_alarms
                }
                aws_connection.publish(
                    topic=PUBLISH_TOPIC,
                    payload=json.dumps(heartbeat_payload),
                    qos=mqtt.QoS.AT_LEAST_ONCE
                )
                print(f"\n[METRICS] Heartbeat dispatched to AWS: {dropped_alarms} noise events filtered.")
            
            # Reset counters whether we published or not
            dropped_alarms = 0
            last_heartbeat_time = current_time

        # --- 2. SENSOR INGESTION ---
        try:
            data, addr = udp_sock.recvfrom(1024) 
        except socket.timeout:
            # If no sensor data arrives within 1 second, loop back to check the heartbeat timer
            continue

        # Check if processing is paused via Dashboard Command & Control
        if not system_is_active:
            continue 

        # --- 3. PARSE EDGE DATA ---
        sensor_data = json.loads(data.decode('utf-8'))
        rf = sensor_data.get("rf_dbm", -100)
        acoustic = sensor_data.get("acoustic_hz", 0)
        seismic = sensor_data.get("seismic_g", 0.0)
        mass = sensor_data.get("mass_kg", 0.0)
        
        alert, status = "None", "All Clear"
        
        # --- 4. MULTI-THREAT DETECTION LOGIC (FOG FILTERING) ---
        # THREAT 1: DRONE (Strong RF, High Pitch, Low Mass)
        if rf > -50 and acoustic > 4000 and mass < 5.0:
            alert, status = "Airspace Drone Breach", "Local Jammer Active"
            
        # THREAT 2: TRESPASSER (Footsteps, Human Mass)
        elif 0.4 <= seismic <= 1.0 and 60.0 <= mass <= 90.0:
            alert, status = "Ground Trespass", "Perimeter Lockdown Engaged"
            
        # THREAT 3: UNAUTHORIZED VEHICLE (Heavy Mass, High Vibration)
        elif seismic > 1.5 and mass > 1000.0:
            alert, status = "Unauthorized Vehicle Approach", "Hydraulic Bollards Raised"
            
        # THREAT 4: FENCE TAMPERING (Metal grinding, low mass)
        elif 2000 <= acoustic <= 3500 and mass < 10.0:
            alert, status = "Fence Tampering / Cutting", "Warning Siren Activated"

        # --- 5. TRANSMISSION ROUTING ---
        if alert != "None":
            print(f"ALERT: {alert} - Executing: {status}")
            payload = {
                "alert": alert,
                "status": status,
                "raw_data_sample": {
                    "rf_signal_strength_dbm": rf,
                    "acoustic_frequency_hz": acoustic,
                    "seismic_vibration_g": seismic,
                    "thermal_object_mass_kg": mass
                }
            }
            
            # Securely publish actual threats to the cloud topic
            aws_connection.publish(
                topic=PUBLISH_TOPIC,
                payload=json.dumps(payload),
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
            print("   -> Threat data dispatched to AWS Cloud.")
        else:
            # Data did not trigger any thresholds. Drop it and log it for the heartbeat metric.
            dropped_alarms += 1

if __name__ == '__main__':
    try:
        aws_conn = connect_to_aws()
        run_fog_logic(aws_conn)
    except KeyboardInterrupt:
        print("\nShutting down Fog Node...")
@echo off
echo [SYSTEM] Initializing Perimeter Sensor Array...

start cmd /k "title Drone Radar && python sensor_drone.py"
start cmd /k "title Fence Monitor && python sensor_fence.py"
start cmd /k "title Seismic Trespass && python sensor_trespass.py"
start cmd /k "title Vehicle Gate && python sensor_vehicle.py"

echo [SYSTEM] All four edge sensors are now running in separate windows!
import random
from datetime import datetime
battery_level=100.0
fuel_level=100.0
temperature_level=20.0
rising=True
voltage_level=random.uniform(3.3,5.0)
def generate_telemetry_snapshot(fault_injection):
    # Simulate telemetry data collection
    global battery_level
    battery_level=battery_level-random.uniform(0.1,0.5)
    if battery_level<0:
        battery_level=0

    global fuel_level
    fuel_level=fuel_level-random.uniform(0.05, 0.2)
    if fuel_level<0:
        fuel_level=0
    
    global temperature_level,rising
    if rising is False:
        temperature_level=temperature_level-random.uniform(0.1,0.5)
    else:
        temperature_level=temperature_level+random.uniform(0.1,0.5)
    if temperature_level>=80:
        rising=False
    elif temperature_level<=20:
        rising=True

    voltage_level=5.0
    if battery_level>50.0:
        voltage_level=random.uniform(3.8,5.0)
    elif battery_level>20.0 and battery_level<50.0:
        voltage_level=random.uniform(3.3,3.8)
    elif battery_level<=20.0:
        voltage_level=random.uniform(3.0,3.3)
    if voltage_level<0:
        voltage_level=0

    if fault_injection["battery"] is True:
        battery_level=random.uniform(0.0,10.0)
    if fault_injection["fuel"] is True:
        fuel_level=random.uniform(0.0,5.0)
    if fault_injection["temperature"] is True:
        temperature_level=random.uniform(90.0,100.0)
    if fault_injection["voltage"] is True:
        voltage_level=random.uniform(2.5,3.3)
    
    data_snapshot = {
        "timestamp": datetime.now(),
        "temperature":temperature_level,
        "battery":battery_level,
        "voltage":voltage_level,
        "fuel":fuel_level
    }
    return data_snapshot

import random
from datetime import datetime
def generate_telemetry_snapshot():
    # Simulate telemetry data collection
    data_snapshot = {
        "timestamp": datetime.now(),
        "temperature":random.uniform(0,80),
        "battery":random.uniform(20,100),
        "voltage":random.uniform(3.3, 5.0),
        "fuel":random.uniform(10,100)
    }
    return data_snapshot

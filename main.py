import time
from simulator.generator import generate_telemetry_snapshot
from monitor.fault_detector import fault_check
from logger.telemetry_logger import log_telemetry

while True:
    data = generate_telemetry_snapshot()
    status = fault_check(data)
    print(data)
    print(status)
    log_telemetry(data, status)
    time.sleep(1)
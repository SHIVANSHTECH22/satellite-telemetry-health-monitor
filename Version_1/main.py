import time
from simulator.generator import generate_telemetry_snapshot
from monitor.fault_detector import fault_check
from logger.telemetry_logger import log_telemetry

while True:
    snapshot = generate_telemetry_snapshot()
    fault = fault_check(snapshot)
    log_telemetry(snapshot, fault)
    print(snapshot)
    print(fault)
    time.sleep(2)
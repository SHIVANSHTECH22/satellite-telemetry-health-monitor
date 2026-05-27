import time
from simulator.generator import generate_telemetry_snapshot
from monitor.fault_detector import fault_check
from logger.telemetry_logger import log_telemetry
fault_injection={
    "battery": False,
    "voltage": False,
    "temperature": False,
    "fuel": False
}
a=input("Do you want to inject fault (yes/no)?:")
if a == "yes":
        value=input("Enter the parameter you wanted to inject fault\n1.battery\n2.temprature\n3.voltage\n4.fuel\n")
        if value == "battery":
            fault_injection["battery"]=True
        elif value == "temprature":
            fault_injection["temperature"]=True
        elif value == "voltage":
            fault_injection["voltage"]=True
        else: 
            fault_injection["fuel"]=True
while True:
    data = generate_telemetry_snapshot(fault_injection)
    status = fault_check(data)
    print(data)
    print(status)
    log_telemetry(data, status)
    time.sleep(1)
    
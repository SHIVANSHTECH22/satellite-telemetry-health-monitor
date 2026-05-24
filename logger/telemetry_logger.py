
import os
import csv

def log_telemetry(snapshot, fault):
    filepath = "data/telemetry_log.csv"
    fieldnames = [
        "timestamp", "temperature", "battery", 
        "voltage", "fuel",
        "temp_status", "battery_status", 
        "voltage_status", "fuel_status"
    ]
    
    file_exists = os.path.exists(filepath)
    
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            "timestamp": snapshot["timestamp"],
            "temperature": snapshot["temperature"],
            "temp_status": fault["temperature"],
            "battery": snapshot["battery"],
            "battery_status": fault["battery"],     
            "voltage": snapshot["voltage"],            
            "voltage_status": fault["voltage"],     
            "fuel": snapshot["fuel"],               
            "fuel_status": fault["fuel"]         
        })
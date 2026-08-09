import argparse
from event_detection_file import event_detection
from log_loader_file import log_loader
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path = args.file
def fault_statistics(event_list, df):
    fault_stats={}
    fault_stats["total_faults"] = len(event_list)
    fault_per_parameter={"temperature":0,"battery":0,"fuel":0, "voltage":0}
    for i in event_list:
        fault_per_parameter[i["parameter"]] += 1
    fault_stats["faults_per_parameter"] = fault_per_parameter
    fault_frequency_per_hour=(fault_stats["total_faults"]*3600)/(df["MET"].iloc[-1])
    fault_stats["fault_frequency_per_hour"]=fault_frequency_per_hour
    count=0
    for i in event_list:
        if i["recovered"]==True:
            count=count+1
    fault_stats["recovery_rate"]=(count/fault_stats["total_faults"])*100
    fault_stats["most_faulted_parameter"]=max(fault_per_parameter, key=fault_per_parameter.get)
    longest_fault_duration=0
    for i in event_list:
        if i["duration"]>longest_fault_duration:
            fault_stats["longest_fault_duration"]=i["duration"]
            longest_fault_duration=i["duration"]
    count_critical=0
    count_warning=0
    for i in event_list:
        
        if i["severity"]=="critical":
            count_critical=count_critical+1
        elif i["severity"]=="warning":
            count_warning=count_warning+1
    fault_stats["severity"]={"warning":count_warning,"critical":count_critical}
    return fault_stats
df, quality_report = log_loader(file_path)
event_list = event_detection(df)
fault = fault_statistics(event_list,df)
print(fault)

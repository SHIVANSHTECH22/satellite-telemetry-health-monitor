import argparse 
from event_detection_file import event_detection
from log_loader_file import log_loader
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path=args.file
def mission_timeline(df,event_list):
    timeline_list=[{
    "MET": df["MET"].iloc[0],
    "timestamp": df["timestamp"].iloc[0],
    "event_type": "MISSION_START",
    "severity": "Nominal",
    "description": "Mission started"
    }]
    for i in event_list:
            dict={
                "MET": i["start_MET"],
                "timestamp": df["timestamp"].iloc[0],
                "event_type": i["event_type"],
                "severity": i["severity"],
                "description": "Fault Detected on " + i["parameter"]
            }
            timeline_list.append(dict)
    dict={
        "MET": df["MET"].iloc[-1],
        "timestamp": df["timestamp"].iloc[-1],
        "event_type": "MISSION_END",
        "severity": "Nominal",
        "description": "Mission END"
    }
    timeline_list.append(dict)
    timeline_list = sorted(timeline_list, key=lambda x: x["MET"])
    return timeline_list
df, quality_report = log_loader(args.file)
event_list = event_detection(df)
timeline = mission_timeline(df, event_list)
print(timeline)

    
    

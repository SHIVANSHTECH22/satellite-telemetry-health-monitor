import argparse
from log_loader_file import log_loader
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path=args.file
def event_detection(df):
    event_list=[]
    thresholds = {
    "battery": {"warning": 20, "critical": 10, "direction": "below"},
    "temperature": {"warning": 35, "critical": 45, "direction": "above"},
    "fuel": {"warning": 20, "critical": 10, "direction": "below"}
    }
    min_duration=3
    for i in thresholds:
        count=0
        event_start=False
        for index, row in df.iterrows():
            para_value=row[i]
            if thresholds[i]["direction"] == "below" :
                if para_value<thresholds[i]["critical"]:
                   breach=True
                   severity="critical"
                elif para_value<thresholds[i]["warning"] :
                    breach=True
                    severity="warning"
                else:
                    breach=False
            elif thresholds[i]["direction"] == "above":
                if para_value>thresholds[i]["critical"]:
                   breach=True
                   severity="critical"
                elif para_value>thresholds[i]["warning"]:
                    breach=True
                    severity="warning"
                else:
                    breach=False
            if breach==True:
                count=count+1
                if count >= min_duration and event_start==False:
                    event_start = True
                    start_MET = row["MET"]
                    trigger_value = row[i]
            else:
                if event_start==True:
                    end_MET= row["MET"]
                    duration=end_MET-start_MET
                    if thresholds[i]["direction"] == "below":
                        event_type = "low_" + i
                    elif thresholds[i]["direction"] == "above":
                        event_type = "high_" + i
                    event = {
                        "event_type": event_type,
                        "parameter": i,
                        "severity": severity,
                        "start_MET": start_MET,
                        "end_MET": end_MET,
                        "duration": duration,
                        "trigger_value": trigger_value,
                        "recovered": True
                    }
                    event_list.append(event)
                    event_start=False
        if event_start == True:
            end_MET = df["MET"].iloc[-1]
            duration = end_MET - start_MET
            if thresholds[i]["direction"] == "below":
                event_type = "low_" + i
            elif thresholds[i]["direction"] == "above":
                event_type = "high_" + i
            event = {
                "event_type": event_type,
                "parameter": i,
                "severity": severity,
                "start_MET": start_MET,
                "end_MET": end_MET,
                "duration": duration,
                "trigger_value": trigger_value,
                "recovered": False
            }
            event_list.append(event)
            event_start = False
    return event_list
df, quality_report = log_loader(args.file)
events = event_detection(df)
print(events)
def convert_to_timeline_events(events):
    timeline_events=[]
    for i in events:
        start_entry = {"event_type": i["parameter"] + "_start", "severity":i["severity"], "timestamp": i["start_MET"]}
        timeline_events.append(start_entry)
                

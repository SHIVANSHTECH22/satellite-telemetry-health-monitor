import argparse
from log_loader_file import log_loader
from event_detection_file import event_detection
from summary_statistics_file import summary_statistics
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path = args.file
def health_score(df, event_list, stats):
    scores={"Battery_score":100, 
          "Thermal_score":100,
          "Fuel_score":100,
          "Overall_score":100}
    for i in event_list:
        if i["parameter"]=="battery":
            if i["severity"]=="critical":
                scores["Battery_score"]-=15
            else:
                scores["Battery_score"]-=10
            scores["Battery_score"] = max(0, scores["Battery_score"])
        elif i["parameter"]=="temperature":
                    if i["severity"]=="critical":
                        scores["Thermal_score"]-=15
                    else:
                        scores["Thermal_score"]-=10
                    scores["Thermal_score"] = max(0, scores["Thermal_score"])
        elif i["parameter"]=="fuel":
                    if i["severity"]=="critical":
                        scores["Fuel_score"]-=15
                    else:
                        scores["Fuel_score"]-=10
                    scores["Fuel_score"] = max(0, scores["Fuel_score"])
    overall_score=scores["Battery_score"] * 0.40 + scores["Fuel_score"] * 0.35 + scores["Thermal_score"] * 0.25
    scores["Overall_score"] = min(overall_score, scores["Battery_score"], scores["Thermal_score"], scores["Fuel_score"])
    return scores
df, quality_report = log_loader(args.file)
event_list = event_detection(df)
stats = summary_statistics(df)
scores = health_score(df, event_list, stats)
print(scores)
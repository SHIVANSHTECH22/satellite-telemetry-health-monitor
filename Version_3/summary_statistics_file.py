import argparse
from log_loader_file import log_loader
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path=args.file
def summary_statistics(df):
    parameter_list=["battery","fuel","temperature","voltage"]
    thresholds = {
    "battery": {"warning_min": 20},
    "temperature": {"warning_max": 35},
    "fuel": {"warning_min": 20},
    "voltage": {"warning_min": 3.5, "warning_max": 4.8}
    }
    trend = "stable"
    stats={}
    for i in parameter_list:
        if "warning_min" in thresholds[i] and "warning_max" in thresholds[i]:
            nominal=(df[i] > thresholds[i]["warning_min"]) & (df[i] < thresholds[i]["warning_max"])
        elif "warning_min" in thresholds[i]:
            nominal=(df[i] > thresholds[i]["warning_min"])
        elif "warning_max" in thresholds[i]:
            nominal=(df[i] < thresholds[i]["warning_max"])
        nominal_percentage = ((nominal.sum()) / (df.shape[0]) * 100)
        avg_rate = ((df[i].diff()) / (df["MET"].diff())).mean()
        if avg_rate > 0.01:
            trend="rising"
        elif avg_rate< -0.01:
            trend = "falling"
        else:
            trend="stable"
        stats[i] = {
            "descriptive": df[i].describe(),
            "rate_of_change": avg_rate,
            "nominal_percentage": nominal_percentage,
            "trend": trend
        } 
    return stats  
df, quality_report = log_loader(args.file)
stats = summary_statistics(df)
print(stats)

import argparse
from event_detection_file import event_detection
from fault_statistics_file import fault_statistics
from generate_report_file import generate_report
from health_score_file import health_score
from log_loader_file import log_loader
from mission_timeline_file import mission_timeline
from summary_statistics_file import summary_statistics
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path = args.file
df, quality_report = log_loader(args.file)
event_list = event_detection(df)
stats = summary_statistics(df)
scores = health_score(df, event_list, stats)
timeline = mission_timeline(df, event_list)
fault = fault_statistics(event_list,df)
generate_report(df, stats, quality_report, event_list, fault, scores, timeline, file_path)
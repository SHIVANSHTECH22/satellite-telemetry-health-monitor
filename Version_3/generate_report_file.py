import csv
import json
import datetime
import argparse
from event_detection_file import event_detection
from fault_statistics_file import fault_statistics
from health_score_file import health_score
from log_loader_file import log_loader
from mission_timeline_file import mission_timeline
from summary_statistics_file import summary_statistics
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path = args.file
def generate_report(df, stats, quality_report, event_list, fault_stats, scores, timeline_list, file_path):
    with open("health_scores.json", "w") as f:
        json.dump(scores, f)
    with open("mission_timeline.json", "w") as f:
            json.dump(str(timeline_list), f)
    if len(event_list) > 0:
        data=event_list
        fieldnames = event_list[0].keys()
        with open("fault_log.csv", "w", newline="") as f:
            writer=csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    else:
        print("Event List is Empty!")
    with open("mission_report.txt", "w") as f:
        f.write("==== MISSION REPORT ====\n")
        f.write("Mission File: "+ file_path +"\n")
        f.write("Date and Time file is created: " + str(datetime.datetime.now()) + "\n")
        f.write("Total Rows: "+str(quality_report["Total Rows"])+"\n")
        f.write("Missing Values: "+str(quality_report["Missing Values"])+"\n")
        f.write("Completeness Percentage: "+str(quality_report["Completeness Percentage"])+"\n")
        f.write("Out_of_Order Timestamps: "+str(quality_report["out_of_order Timestamps"])+"\n")
        f.write("Duplicate Timestamps: "+str(quality_report["Duplicate Timestamps"])+"\n")
        f.write("Impossible Counts: "+str(quality_report["Impossible Count"])+"\n")
        for parameter in stats:
            f.write("\n"+"Parameter: "+ parameter+"\n")
            f.write("Rate Of Change: "+ str(stats[parameter]["rate_of_change"]) +"\n")
            f.write("Nominal Percentage: "+ str(stats[parameter]["nominal_percentage"]) +"\n")
            f.write("Trend: "+ str(stats[parameter]["trend"]) +"\n")
        f.write("\n"+"Battery Score: "+str(scores["Battery_score"])+"\n")
        f.write("Thermal Score: "+str(scores["Thermal_score"])+"\n")
        f.write("Fuel Score: "+str(scores["Fuel_score"])+"\n")
        f.write("Overall Score: "+str(scores["Overall_score"])+"\n")
        f.write("Total Stats: "+str(fault_stats["total_faults"])+"\n")
        f.write("Fault Frequency Per Hour: "+str(fault_stats["fault_frequency_per_hour"])+"\n")
        f.write("Recovery Rate: "+str(fault_stats["recovery_rate"])+"\n")
        f.write("Most Faulted Parameters: "+fault_stats["most_faulted_parameter"]+"\n")
        f.write("Longest Fault Duration: "+str(fault_stats["longest_fault_duration"])+"\n")
        for para in fault_stats["faults_per_parameter"]:
            f.write(para + ": " + str(fault_stats["faults_per_parameter"][para])+"\n")
        for sever in fault_stats["severity"]:
            f.write("Severity: "+ str(fault_stats["severity"][sever])+"\n")
        for item in timeline_list:
            f.write("MET: "+str(item["MET"])+"\n")
            f.write("Timestamp: "+str(item["timestamp"])+"\n")
            f.write("Event Type: "+item["event_type"]+"\n")
            f.write("Severity: "+item["severity"]+"\n")
            f.write("Description: "+item["description"]+"\n")
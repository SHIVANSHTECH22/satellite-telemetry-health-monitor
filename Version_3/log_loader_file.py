import argparse
import pandas as pd
parser = argparse.ArgumentParser(description="Satellite Telemetry Log Analyzer V3")
parser.add_argument("--file", required=True, help="Path to the telemetry CSV log file. Example: --file telemetry_log.csv")
args=parser.parse_args()
file_path=args.file
def log_loader(file_path):
    try:
        df=pd.read_csv(file_path)
        print(f"Log loaded successfully — {df.shape[0]} rows found")
    except FileNotFoundError:
        print(f"Error: File not found — {file_path}")
        exit()

    #BLOCK - 02

    csv_columns=["timestamp","battery","fuel","temperature","voltage","battery_status","fuel_status","temp_status","voltage_status"]
    columns_not_exist=[]
    for i in csv_columns:
             if i in df.columns:
                   continue
             else:
                  columns_not_exist.append(i)
    if len(columns_not_exist) == 0:
          print("No columns is missing in file")
    else:
          print("Missing Columns: ",columns_not_exist)
          exit()

    # BLOCK - 03
    missing_value_dataframe=0
    for i in df.columns:
        missing_value_column=df[i].isnull().sum()
        print("Missing Value in",i,"are",missing_value_column)
        missing_value_dataframe=missing_value_dataframe+missing_value_column
    print("Total Missing Value in Dataframe are: ",missing_value_dataframe)
    total_cells = df.shape[0]*df.shape[1]
    valid_cells = total_cells - missing_value_dataframe
    completeness = valid_cells / total_cells * 100
    print("Data Completeness: ",round(completeness,2),"%")

    # BLOCK - 04

    df["timestamp"]=pd.to_datetime(df["timestamp"])
    time_diff = df["timestamp"].diff()
    out_of_order_count = (time_diff < pd.Timedelta(0)).sum()
    if out_of_order_count==0:
        print("Timestamps are in order — no issues found")
    else:
         print(f"Out of order timestamps found: {out_of_order_count}")

    # BLOCK - 05 

    duplicate_count=df["timestamp"].duplicated().sum()
    if duplicate_count==0:
        print("No duplicate Found")
    else:
         print(f"Duplicates: {duplicate_count}")

    # BLOCK - 06

    df["MET"]=(df["timestamp"]-df["timestamp"].iloc[0]).dt.total_seconds()
    print(f'Mission Duration: {df["MET"].iloc[-1]}')

    # BLOCK - 07

    temperature_minimum = -100
    temperature_maximum = 200
    battery_minimum = 0
    battery_maximum = 100
    fuel_minimum = 0
    fuel_maximum = 100
    voltage_minimum = 0
    voltage_maximum = 10

    temp_impossible=(df["temperature"]>=temperature_maximum) | (df["temperature"] < temperature_minimum)
    battery_impossible=(df["battery"]>battery_maximum) | (df["battery"]<battery_minimum)
    fuel_impossible=(df["fuel"]>fuel_maximum) | (df["fuel"]<fuel_minimum)
    voltage_impossible=(df["voltage"]>voltage_maximum) | (df["voltage"]<voltage_minimum)

    df["impossible_flag"]=temp_impossible | battery_impossible | voltage_impossible | fuel_impossible

    impossible_count = df["impossible_flag"].sum()
    print (f"Impossible values flagged: {impossible_count}")

    quality_report={
        "Total Rows": df.shape[0],
        "Missing Values": missing_value_dataframe,
        "Completeness Percentage": round(completeness,2),
        "out_of_order Timestamps": out_of_order_count,
        "Duplicate Timestamps": duplicate_count,
        "Impossible Count": impossible_count
    }

    return df,quality_report

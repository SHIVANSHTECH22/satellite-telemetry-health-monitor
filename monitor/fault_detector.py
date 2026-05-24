def fault_check(data_snapshot):
    fault={}
    if data_snapshot["temperature"]>90:
        fault["temperature"]="Critical"
    elif data_snapshot["temperature"]>80:
        fault["temperature"]="Warning"
    else :
        fault["temperature"]="Normal"
    if data_snapshot["battery"]<5:
        fault["battery"]="Critical!!"
    elif data_snapshot["battery"]<20:
        fault["battery"]="Warning"
    else :
        fault["battery"]="Normal"
    if data_snapshot["voltage"]<3.3:
        fault["voltage"]="Critical!!"
    elif data_snapshot["voltage"]<3.6:
        fault["voltage"]="Warning"
    else :
        fault["voltage"]="Normal"
    if data_snapshot["fuel"]<5:
        fault["fuel"]="Critical!!"
    elif data_snapshot["fuel"]<15:
        fault["fuel"]="Warning"
    else :
        fault["fuel"]="Normal"
    return fault
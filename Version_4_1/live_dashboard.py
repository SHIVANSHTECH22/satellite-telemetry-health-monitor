import pandas as pd 
import matplotlib.pyplot as plt 
def update_dashboard(file_path):
     while True:
         df=pd.read_csv(file_path) 
         last_rows=df.tail(50)
         plt.clf()  
         temp_value = last_rows["temperature"].iloc[-1]
         if temp_value > 90:
            temp_color = "red"
         elif temp_value >75:
            temp_color = "orange"
         else:
            temp_color = "green"
         voltage_value = last_rows["voltage"].iloc[-1]
         if voltage_value <3.3:
            voltage_color = "red"
         elif voltage_value <3.5:
            voltage_color = "orange"
         else:
            voltage_color = "green"
         battery_value = last_rows["battery"].iloc[-1]
         if battery_value < 10:
            battery_color = "red"
         elif battery_value <20:
            battery_color = "orange"
         else:
            battery_color = "green"
         fuel_value = last_rows["fuel"].iloc[-1]
         if fuel_value < 5:
            fuel_color = "red"
         elif fuel_value <15:
            fuel_color = "orange"
         else:
            fuel_color = "green"  
         fig, axes = plt.subplots(nrows=4, ncols=1)   
         axes[0].plot(last_rows["timestamp"], last_rows["temperature"], color=temp_color)
         axes[1].plot(last_rows["timestamp"], last_rows["voltage"], color=voltage_color)
         axes[2].plot(last_rows["timestamp"], last_rows["battery"], color=battery_color)
         axes[3].plot(last_rows["timestamp"], last_rows["fuel"], color=fuel_color)
         axes[0].set_title("temperature")
         axes[0].set_ylabel("°C")
         axes[2].set_title("battery")
         axes[2].set_ylabel("%")
         axes[1].set_title("voltage")
         axes[1].set_ylabel("V")
         axes[3].set_title("fuel")
         axes[3].set_ylabel("unit") # im writing unit because unit of fuel depends on fuel type in satellite
         plt.tight_layout()
         plt.pause(1)
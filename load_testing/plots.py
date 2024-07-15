import pandas as pd
import matplotlib.pyplot as plt

# Data
data = {
    "Number of Rooms": [60, 60, 60, 60, 60, 60, 60, 60, 60, 60],
    "Number of Clients": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
    "CPU Utilization Percentage": [3.80, 6.30, 8.40, 10.50, 11.30, 20.50, 22.40, 23.30, 25.70, 28.70],
    "Average Packet Loss Percentage": [0.85, 0.82, 1.67, 1.71, 0.85, 1.12, 1.50, 6.85, 19.60, 36.99],
    "Standard Deviation in Packet Loss Percentage": [0.29, 0.15, 1.04, 1.06, 0.01, 1.03, 0.70, 6.45, 3.60, 12.91],
    "Average Join Time (seconds)": [0.03, 0.07, 0.11, 0.39, 0.42, 0.47, 0.87, 1.21, 1.2, 1.26],
    "Standard Deviation in Join Time (seconds)": [0.008, 0.018, 0.04, 0.06, 0.12, 0.1, 0.3, 0.92, 0.5, 0.95],
    "Memory Utilization Percentage": [22.20, 22.70, 23.00, 23.60, 24.00, 24.50, 25.50, 26.00, 26.00, 26.90],
    "Network Throughput Achieved (Mbps)": [15.49, 31.01, 46.57, 61.9, 77.66, 91.08, 94.5, 100, 104.5, 107.3],
    "Ideal Network Throughput (Mbps)": [15.625, 31.25, 46.875, 62.5, 78.125, 93.75, 110.45, 124.99, 144.5, 156.25],
}

# Create DataFrame
df = pd.DataFrame(data)

# Adjust the bar width
bar_width = 15

# CPU Utilization Vs Number of Clients (Column Chart)
plt.figure(figsize=(12, 7))
plt.bar(df["Number of Clients"], df["CPU Utilization Percentage"], width=bar_width, color='b')
plt.xlabel('Number of Clients', fontsize=18)
plt.ylabel('CPU Utilization Percentage', fontsize=18)
plt.title('CPU Utilization Vs Number of Clients (60 Rooms)', fontsize=18)
plt.xticks(df["Number of Clients"], fontsize=15)  # Set x-ticks to match the data
plt.yticks(fontsize=15)
plt.grid(True)
plt.savefig('cpu_utilization_vs_clients (60 Rooms).png')
plt.close()

# Average Packet Loss Percentage and Standard Deviation of Packet Loss Percentage Vs Number of Clients (Bars with Error Bars)
plt.figure(figsize=(12, 7))
plt.bar(df["Number of Clients"], df["Average Packet Loss Percentage"], width=bar_width, color='r', label='Average Packet Loss Percentage')
plt.errorbar(df["Number of Clients"], df["Average Packet Loss Percentage"], yerr=df["Standard Deviation in Packet Loss Percentage"], fmt='o', color='black', capsize=5)
plt.xlabel('Number of Clients', fontsize=18)
plt.ylabel('Packet Loss Percentage', fontsize=18)
plt.title('Packet Loss Percentage Vs Number of Clients (60 Rooms)', fontsize=18)
plt.xticks(df["Number of Clients"], fontsize=15)  # Set x-ticks to match the data
plt.yticks(fontsize=15)
plt.legend(fontsize=16)
plt.grid(True)
plt.savefig('packet_loss_vs_clients (60 Rooms).png')
plt.close()

# Average Join Time and Standard Deviation of Join Time Vs Number of Clients (Bars with Error Bars)
plt.figure(figsize=(12, 7))
plt.bar(df["Number of Clients"], df["Average Join Time (seconds)"], width=bar_width, color='g', label='Average Join Time (seconds)')
plt.errorbar(df["Number of Clients"], df["Average Join Time (seconds)"], yerr=df["Standard Deviation in Join Time (seconds)"], fmt='o', color='black', capsize=5)
plt.xlabel('Number of Clients', fontsize=18)
plt.ylabel('Join Time (seconds)', fontsize=18)
plt.title('Join Time Vs Number of Clients (60 Rooms)', fontsize=18)
plt.xticks(df["Number of Clients"], fontsize=15)  # Set x-ticks to match the data
plt.yticks(fontsize=15)
plt.legend(fontsize=16)
plt.grid(True)
plt.savefig('join_time_vs_clients (60 Rooms).png')
plt.close()

# Plot Network Throughput Achieved and Ideal Throughput vs Number of Clients
plt.figure(figsize=(12, 7))
plt.plot(df["Number of Clients"], df["Network Throughput Achieved (Mbps)"], marker='o', linestyle='-', color='b', label='Network Throughput Achieved (Mbps)')
plt.plot(df["Number of Clients"], df["Ideal Network Throughput (Mbps)"], marker='o', linestyle='--', color='r', label='Ideal Network Throughput (Mbps)')
plt.xlabel('Number of Clients', fontsize=18)
plt.ylabel('Network Throughput (Mbps)', fontsize=18)
plt.title('Network Throughput Achieved vs Ideal Throughput vs Number of Clients (30 Rooms)', fontsize=18)
plt.legend(fontsize=16)
plt.grid(True)
plt.xticks(df["Number of Clients"], fontsize=15)  # Set x-ticks to match the data
plt.yticks(fontsize=15)
plt.savefig('network_throughput_comparison (30 Rooms).png')
plt.close()

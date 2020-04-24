import numpy as np
import pandas as pd
import re
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Plot throughput.')
parser.add_argument('--start-time', default=0, type=int)
parser.add_argument('--end-time', default=20, type=int)
parser.add_argument('--save-path', type=str)
args = parser.parse_args()
start = args.start_time
end = args.end_time
save_path = args.save_path


def clean(filename, start, end):
    filename = open(filename, 'r')
    throughput_file = []
    keep = False
    for i in filename.readlines():
        # print(i)
        i = i.strip()
        if i.endswith('Bandwidth'):
            # print('here')
            keep = True
            # continue
        if keep:
            throughput_file.append(i)
    # print(len(throughput_file))

    throughput_data = []
    for i in range(1,len(throughput_file)):
        row = re.match(r"\[[\s]*([\d]+)\]\s+(\d+\.\d)-\s*(\d+\.\d) sec\s+\d+\.?\d* \w*Bytes\s+(\d+\.?\d*) Mbits/sec", throughput_file[i])
        if row:
            row = [float(s) for s in row.groups(0)]
            row[3] = row[3] * 1000 * 1000
            throughput_data.append(row)
            continue
        row = re.match(r"\[[\s]*([\d]+)\]\s+(\d+\.\d)-\s*(\d+\.\d) sec\s+\d+\.?\d* \w*Bytes\s+(\d+\.?\d*) Kbits/sec", throughput_file[i])
        if row:
            row = [float(s) for s in row.groups(0)]
            row[3] = row[3] * 1000
            throughput_data.append(row)
            continue
        row = re.match(r"\[[\s]*([\d]+)\]\s+(\d+\.\d)-\s*(\d+\.\d) sec\s+\d+\.?\d* \w*Bytes\s+(\d+\.?\d*) bits/sec", throughput_file[i])
        if row:
            row = [float(s) for s in row.groups(0)]
            throughput_data.append(row)
            continue
        if not row:
            # print("NOOOOOOOOO!!")
            continue

    print('throughput_data len:', len(throughput_data))

    # print('Enter start time:')
    # start = input()
    # print('Enter end time:')
    # end = input()

    # start = float(start) # 0
    # end = float(end) # 20
    # start = float(0)
    # end = float(20)

    # ID, start, end, bandwidth
    # [[4, 0.0, 2.0, 2632], ...]
    # tmp = [[4, 0.0, 2.0, 2632], [4, 2.0, 4.0, 262], [4, 4.0, 6.0, 632], [4, 0.0, 6.0, 32]]
    throughput_df = pd.DataFrame(throughput_data, columns=['ID', 'start', 'end', 'bandwidth'])

    new_df = throughput_df.loc[(throughput_df['start'] >= start) & (throughput_df['end'] <= end) & (throughput_df['end'] - throughput_df['start'] == 2)]
    print('dataframe len:', len(new_df))

    return new_df['bandwidth'].sum() / (end - start) / 1000

# start = input("Enter start time:")
# end = input("Enter end time:")
# try:
#     start = int(start)
#     end = int(end)
#     print("Start time is {} and end time is {}.".format(start, end))
# except ValueError:
#     try:
#         start = float(start)
#         end = float(end)
#         print("Input is a float  number. ({}, {})".format(start, end))
#     except ValueError:
#         print("No.. input is not a number. It's a string")


# new_df_bandwidth = clean('throughput', start, end)
# print(new_df_bandwidth)

import os

cubic_files = []
for filename in os.listdir('throughput_txt/cubic'):
    if filename.endswith('.txt'):
        cubic_files.append(filename)
# print(cubic_files)
cubic_bandwidth = []
for filename in cubic_files:
    print(filename)
    node_num = filename.strip().split('.')[0].split('_')[-1]
    cubic_bandwidth.append([int(node_num), clean(os.path.join('throughput_txt/cubic', filename), start, end)])
cubic_bandwidth = np.array(sorted(cubic_bandwidth, key=lambda x: x[0]))
print(cubic_bandwidth)


dctcp_files = []
for filename in os.listdir('throughput_txt/dctcp'):
    if filename.endswith('.txt'):
        dctcp_files.append(filename)
# print(dctcp_files)
dctcp_bandwidth = []
for filename in dctcp_files:
    print(filename)
    node_num = filename.strip().split('.')[0].split('_')[-1]
    dctcp_bandwidth.append([int(node_num), clean(os.path.join('throughput_txt/dctcp', filename), start, end)])
dctcp_bandwidth = np.array(sorted(dctcp_bandwidth, key=lambda x: x[0]))
print(dctcp_bandwidth)


# print(cubic_bandwidth[:,0], cubic_bandwidth[:,1])

# plot data
fig = plt.figure()
fig.suptitle('Throughput Comparison', fontsize=16)
plt.xlabel('Node Numbers', fontsize=12)
plt.ylabel('Throughput (Kbytes)', fontsize=12)
plt.plot(cubic_bandwidth[:,0], cubic_bandwidth[:,1], 'b', label="cubic")
plt.plot(dctcp_bandwidth[:,0], dctcp_bandwidth[:,1], 'r', label="dctcp")
plt.grid(True)
plt.legend()
fig.savefig(save_path)

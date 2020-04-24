# Sample cmd:
# In-case
# python3 qlen_plot.py --cubic testdir32cubic/qlen_rack0-eth5.txt --dctcp testdir32dctcp/qlen_rack0-eth5.txt --save_path incast32_qlen.png
# python3 qlen_plot.py --cubic testdir64cubic/qlen_rack0-eth5.txt --dctcp testdir64dctcp/qlen_rack0-eth5.txt --save_path incast64_qlen.png
# python3 qlen_plot.py --cubic testdir128cubic/qlen_rack0-eth5.txt --dctcp testdir128dctcp/qlen_rack0-eth5.txt --save_path incast128_qlen.png
# Out-cast
# python3 qlen_plot.py --cubic outcast8cubic/qlen_edge0-eth7.txt --dctcp outcast8dctcp/qlen_edge0-eth7.txt --save_path outcast8_qlen.png
# python3 qlen_plot.py --cubic outcast32cubic/qlen_edge0-eth9.txt --dctcp outcast32dctcp/qlen_edge0-eth9.txt --save_path outcast32_qlen.png
# python3 qlen_plot.py --cubic outcast72cubic/qlen_edge0-eth11.txt --dctcp outcast72dctcp/qlen_edge0-eth11.txt --save_path outcast72_qlen.png
# python3 qlen_plot.py --cubic outcast128cubic/qlen_edge0-eth13.txt --dctcp outcast128dctcp/qlen_edge0-eth13.txt --save_path outcast128_qlen.png

import matplotlib.pyplot as plt
import numpy as np
import argparse
import os

# parse argument
def file_path(string):
    if os.path.isfile(string):
        return string
    else:
        raise Exception('filename error')

def get_data(filename):
    timestamp = []
    qlen = []
    with open(filename) as f:
        for line in f:
            line = line.split(',')
            timestamp.append(float(line[0]))
            qlen.append(int(line[1]))
    timestamp = np.array(timestamp) - min(timestamp)
    qlen = np.array(qlen)
    return timestamp, qlen

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot qlen.')
    parser.add_argument('--cubic', type=file_path)
    parser.add_argument('--dctcp', type=file_path)
    parser.add_argument('--save_path')
    args = parser.parse_args()

    # retrieve data
    cubic_timestamp, cubic_qlen = get_data(args.cubic)
    dctcp_timestamp, dctcp_qlen = get_data(args.dctcp)

    # plot data
    fig = plt.figure()
    fig.suptitle('Queue Length Comparison', fontsize=16)
    plt.xlabel('Timestamp (s)', fontsize=12)
    plt.ylabel('Queue Length (bytes)', fontsize=12)
    plt.plot(cubic_timestamp, cubic_qlen, 'b', label="cubic")
    plt.plot(dctcp_timestamp, dctcp_qlen, 'r', label="dctcp")
    plt.grid(True)
    plt.legend()
    fig.savefig(args.save_path)

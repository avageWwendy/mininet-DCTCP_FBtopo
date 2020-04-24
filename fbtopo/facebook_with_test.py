from mininet.topo import Topo
from mininet.node import OVSKernelSwitch as Switch
from mininet.nodelib import LinuxBridge
from mininet.node import CPULimitedHost
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from time import sleep, time

import sys
import multiprocessing
from subprocess import Popen, PIPE
import re
import os
import argparse


HOST_PER_NODE       = 2
LINK_BW             = 40
LINK_DELAY          = '1ms'
NUM_FRABRIC_SWITCH  = 4
NUM_SPINE_SWITCH    = NUM_FRABRIC_SWITCH * NUM_FRABRIC_SWITCH
SWITCH_TYPE         = 'ovsbr,stp=1'
MAX_QUEUE_SIZE      = 1000

parser = argparse.ArgumentParser(description="DCTCP tester (FacebookFatTree topology)")

parser.add_argument('--size', '-s',
                    dest="size",
                    action="store",
                    help="topo size",
                    default=4)

parser.add_argument('--congestion', '-c',
                    dest="congestion",
                    action="store",
                    help="congestion control protocol, dctcp or cubic",
                    required=True)

parser.add_argument('--time', '-t',
                    dest="duration",
                    action="store",
                    help="test time in seconds",
                    default=30)

parser.add_argument('--output', '-o',
                    dest="dir",
                    action="store",
                    help="output directory",
                    required=True)

parser.add_argument('--queue', '-q',
                    dest="queue_len",
                    action="store",
                    help="max queue length",
                    default=MAX_QUEUE_SIZE)

parser.add_argument('--delay', '-d',
                    dest="link_delay",
                    action="store",
                    help="link delay",
                    default=LINK_DELAY)

parser.add_argument('--bandwidth', '-b',
                    dest="bandwidth",
                    action="store",
                    help="link bandwidth",
                    default=LINK_BW)

parser.add_argument('--testcase', '-T',
                    dest="case",
                    action="store",
                    help="testcases: mix, incast or outcast",
                    required=True)

args = parser.parse_args()
path = os.path.join(os.getcwd(), args.dir)
if not os.path.exists(path):
    os.makedirs(path)


def progress(t):
    while t > 0:
        print('  %3d seconds left  \r' % (t))
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print('\r\n')

class StarTopo(Topo):

    def __init__(self, n=3, bw=100):
        # Add default members to class.
        super(StarTopo, self ).__init__()

        # Host and link configuration
        hconfig = {'cpu': -1}
        ldealay_config = {'bw': bw, 'delay': LINK_DELAY,
            'max_queue_size': 1000000
        } 
        lconfig = {'bw': bw, 
           'max_queue_size': int(100000),
           'delay': LINK_DELAY,
           'enable_ecn': True,
           'bw': LINK_BW
        }

        # Create switch and host nodes
        for i in xrange(n):
            self.addHost('host_%d' % (i+1), **hconfig)

        self.addSwitch('s1',)

        self.addLink('host_1', 's1', **lconfig)
        for i in xrange(1, n):
            self.addLink('host_%d' % (i+1), 's1', **ldealay_config)


class FacebookFatTree(Topo):
    def __init__(self, num_TOR=48): 
        # Initialize topology
        Topo.__init__(self)

        # create elements
        rack_switches = []
        for i in range(num_TOR * num_TOR):
            rack_switches.append(self.addSwitch("rack_%s" % str(i), switch=SWITCH_TYPE))
        edge_switches = []
        for i in range(NUM_FRABRIC_SWITCH * num_TOR):
            edge_switches.append(self.addSwitch("edge_%s" % str(i), switch=SWITCH_TYPE))
        spine_switches = []
        for i in range(NUM_SPINE_SWITCH):
            spine_switches.append(self.addSwitch("spine_%s" % str(i), switch=SWITCH_TYPE))
        print("finished creating elements")
        # add links from spine to edge
        lconfig_upper = {
           'bw': int(args.bandwidth), 
           'max_queue_size': int(args.queue_len),
           'delay': args.link_delay,
           'enable_ecn': True if args.congestion == "dctcp" else False,
        }

        lconfig_lower = {
           'bw': int(args.bandwidth)/4/HOST_PER_NODE, 
           'max_queue_size': int(args.queue_len),
           'delay': args.link_delay,
           'enable_ecn': True if args.congestion == "dctcp" else False,
        }
        for i in range(len(spine_switches)):
            spine = spine_switches[i]
            idx_offset = (i // NUM_FRABRIC_SWITCH) * num_TOR
            for j in range(num_TOR):
                self.addLink(spine, edge_switches[idx_offset+j], **lconfig_upper)
        print("finished creating spine-edge")

        # add links from edge to rack
        for i in range(len(edge_switches)):
            edge = edge_switches[i]
            idx_offset = (i % num_TOR) * num_TOR
            for j in range(num_TOR):
                self.addLink(edge, rack_switches[idx_offset+j], **lconfig_upper)
        print("finished creating edge-rack")

        # add hosts to rack
        h = 0
        for rack in rack_switches:
            for i in range(HOST_PER_NODE):
                self.addLink(rack, self.addHost("host_%s" % str(h)), **lconfig_lower)
                h += 1
        print("finished creating hosts")

        if (args.case == "outcast"):
        # add outer host to one edge switch
            self.addLink(edge_switches[0], self.addHost("outer"), **lconfig_lower)
            print("outer eth:", NUM_FRABRIC_SWITCH+num_TOR+1)

# topos = { 'facebook_fattree': ( lambda: FacebookFatTree(4) ) }



# Source: https://github.com/mininet/mininet/wiki/Introduction-to-Mininet#creating                                                                                                                                                                                   

from mininet.net import Mininet
from mininet.node import Controller
from mininet.log import setLogLevel

import os

default_dir = "."

def monitor_qlen(iface, interval_sec = 0.1, fname='%s/qlen.txt' % default_dir):
    """qdisc htb 5: root refcnt 2 r2q 10 default 1 direct_packets_stat 0 direct_qlen 1000
       Sent 108732374 bytes 71875 pkt (dropped 0, overlimits 15535 requeues 0) 
       backlog 0b 0p requeues 0
       qdisc netem 10: parent 5:1 limit 100000
       Sent 108732374 bytes 71875 pkt (dropped 0, overlimits 0 requeues 0) 
       backlog 0b 0p requeues 0"""
    pat_queued = re.compile(r'backlog\s[^\s]+\s([\d]+)p')
    cmd = "tc -s qdisc show dev %s" % (iface)
    ret = []
    open(fname, 'w').write('')
    while 1:
        p = Popen(cmd, shell=True, stdout=PIPE)
        output = p.stdout.read()
        # Not quite right, but will do for now
        matches = pat_queued.findall(output)
        if matches and len(matches) > 1:
            ret.append(matches[1])
            t = "%f" % time()
            open(fname, 'a').write(t + ',' + matches[1] + '\n')
        sleep(interval_sec)
    return

class POXBridge(Controller):                                                                         
    "Custom Controller class to invoke POX forwarding.l2_learning"                                     
    def start( self ):                                                                                 
        "Start POX learning switch"                                                                    
        self.pox = '%s/pox/pox.py' % os.environ[ 'HOME' ]                                              
        self.cmd( self.pox, 'forwarding.l2_learning &' )                                               
    def stop( self ):                                                                                  
        "Stop POX"                                                                                     
        self.cmd( 'kill %' + self.pox )                                                                
                                                                                                       

def IncastTest():
    num_TOR = int(args.size)
    topo = FacebookFatTree(num_TOR)
    host_number = num_TOR*num_TOR*HOST_PER_NODE
    print(host_number)
    net = Mininet(topo=topo, host=CPULimitedHost, 
                  switch=LinuxBridge,
                  link=TCLink, autoStaticArp=True)
    print("end create net")
    net.start()
    net.waitConnected()

    h1 = net.getNodeByName('host_0')
    print(h1.cmd('ping -c 2 10.0.0.2'))
    h1.sendCmd('iperf -s -t %d -i 2 > %s/iperf_host_0.txt' % (int(args.duration) + 5, path))

    clients = [net.getNodeByName('host_%d' % (i)) for i in xrange(1, host_number)]
    sleep(1)

    monitors = []
    # add more switch interface for fat-tree topo
    # may consider using mtr to test ping, -s PACKETSIZE, --psize PACKETSIZE
    monitor = multiprocessing.Process(target=monitor_qlen, args=('rack_0-eth5', 0.1, '%s/qlen_rack0-eth5.txt' % path))
    monitor.start()
    monitors.append(monitor)

    for i in xrange(1, host_number):
        node_name = 'host_%d' % (i)
        cmd = 'iperf -c 10.0.0.1 -t %d -i 2 -O 2 -Z %s' % (int(args.duration), args.congestion)
        # cmd = 'iperf -c 10.0.0.1 -t %d -i 2 -O 2 -Z %s > %s/iperf_%s.txt' % (int(args.duration), args.congestion ,path, node_name)
        h = net.getNodeByName(node_name)
        h.sendCmd(cmd)
    
    progress(int(args.duration))
    for monitor in monitors:
        monitor.terminate()

    net.getNodeByName('host_0').pexec("/sbin/ifconfig > %s/ifconfig.txt" % path, shell=True)
    for i in xrange(0, host_number):
        net.getNodeByName('host_%d' % (i)).waitOutput()
        print('host_%d finished' % (i))
    net.stop()

def OutcastTest():
    num_TOR = int(args.size)
    topo = FacebookFatTree(num_TOR)
    host_number = num_TOR*num_TOR*HOST_PER_NODE
    print(host_number)
    net = Mininet(topo=topo, host=CPULimitedHost, 
                  switch=LinuxBridge,
                  link=TCLink, autoStaticArp=True)
    print("end create net")
    net.start()
    net.waitConnected()

    h1 = net.getNodeByName('host_0')
    print(h1.cmd('ping -c 2 10.0.0.2'))
    
    clients = [net.getNodeByName('host_%d' % (i)) for i in xrange(1, host_number)]
    sleep(1)

    monitors = []
    # add more switch interface for fat-tree topo
    # may consider using mtr to test ping, -s PACKETSIZE, --psize PACKETSIZE
    monitor = multiprocessing.Process(target=monitor_qlen, args=('edge_0-eth%d' % (NUM_FRABRIC_SWITCH+num_TOR+1), 0.1, '%s/qlen_edge0-eth%d.txt' % (path, NUM_FRABRIC_SWITCH+num_TOR+1)))
    monitor.start()
    monitors.append(monitor)
    
    server = net.getNodeByName('outer')
    server.sendCmd('iperf -s -t %d -i 2 > %s/iperf_outer.txt' % (int(args.duration) + 5, path))
    for i in xrange(1, host_number):
        node_name = 'host_%d' % (i)
        cmd = 'iperf -c %s -t %d -i 2 -O 2 -Z %s' % (server.IP(), int(args.duration), args.congestion)
        # cmd = 'iperf -c %s -t %d -i 2 -O 2 -Z %s > %s/iperf_%s.txt' % (server.IP(), int(args.duration), args.congestion, path, node_name)
        h = net.getNodeByName(node_name)
        h.sendCmd(cmd)
    
    progress(int(args.duration))
    for monitor in monitors:
        monitor.terminate()

    net.getNodeByName('outer').pexec("/sbin/ifconfig > %s/ifconfig.txt" % path, shell=True)
    for i in xrange(0, host_number):
        net.getNodeByName('host_%d' % (i)).waitOutput()
        print('host_%d finished' % (i))
    net.getNodeByName('outer').waitOutput()
    print('outer finished')
    net.stop()


if __name__ == '__main__':
    if (args.congestion == "dctcp"):
        Popen("sysctl -w net.ipv4.tcp_congestion_control=dctcp", shell=True).wait()
    else:
        Popen("sysctl -w net.ipv4.tcp_congestion_control=cubic", shell=True).wait()
    if (args.case == 'incast'):
        IncastTest()
    elif (args.case == 'outcast'):
        OutcastTest()


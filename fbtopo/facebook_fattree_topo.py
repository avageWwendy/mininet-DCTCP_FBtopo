import sys
from mininet.topo import Topo
from mininet.nodelib import LinuxBridge as Switch
from mininet.node import CPULimitedHost
from mininet.node import RemoteController
from mininet.link import TCLink
from time import sleep, time
import multiprocessing
from subprocess import Popen, PIPE
import re


HOST_PER_NODE       = 2
LINK_BW             = 10
LINK_DELAY          = '.075ms'
NUM_FRABRIC_SWITCH  = 4
NUM_SPINE_SWITCH    = NUM_FRABRIC_SWITCH * NUM_FRABRIC_SWITCH
SWITCH_TYPE         = 'lxbr'
MAX_QUEUE_SIZE      = 1000

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
        # spine interface: 4 0 + 4
        # edge interface: 8 4 + 4
        # rack interface: 6 4 + 2
        Topo.__init__(self)

        # create elements
        rack_switches = []
        lconfig = {'stp': 1, 
           'max_queue_size': int(100000),

        }
        for i in range(num_TOR * num_TOR):
            rack_switches.append(self.addSwitch("rack_%s" % str(i), cls=Switch))
        edge_switches = []
        for i in range(NUM_FRABRIC_SWITCH * num_TOR):
            edge_switches.append(self.addSwitch("edge_%s" % str(i), cls=Switch))
        spine_switches = []
        for i in range(NUM_SPINE_SWITCH):
            spine_switches.append(self.addSwitch("spine_%s" % str(i), cls=Switch))
        print("finished creating elements")
        # add links from spine to edge
        for i in range(len(spine_switches)):
            spine = spine_switches[i]
            idx_offset = (i // NUM_FRABRIC_SWITCH) * num_TOR
            for j in range(num_TOR):
                self.addLink(spine, edge_switches[idx_offset+j], bw=LINK_BW, delay=LINK_DELAY, max_queue_size=MAX_QUEUE_SIZE)
        print("finished creating spine-edge")

        # add links from edge to rack
        for i in range(len(edge_switches)):
            edge = edge_switches[i]
            idx_offset = (i % num_TOR) * num_TOR
            for j in range(num_TOR):
                self.addLink(edge, rack_switches[idx_offset+j], bw=LINK_BW, delay=LINK_DELAY, max_queue_size=MAX_QUEUE_SIZE)
        print("finished creating edge-rack")

        # add hosts to rack
        h = 0
        for rack in rack_switches:
            for i in range(HOST_PER_NODE):
                self.addLink(rack, self.addHost("host_%s" % str(h)))
                h += 1
        print("finished creating hosts")

# topos = { 'facebook_fattree': ( lambda: FacebookFatTree(4) ) }



# Source: https://github.com/mininet/mininet/wiki/Introduction-to-Mininet#creating                                                                                                                                                                                   

from mininet.net import Mininet
from mininet.node import Controller
from mininet.log import setLogLevel

import os

class POXBridge(Controller):                                                                         
    "Custom Controller class to invoke POX forwarding.l2_learning"                                     
    def start( self ):                                                                                 
        "Start POX learning switch"                                                                    
        self.pox = '%s/pox/pox.py' % os.environ[ 'HOME' ]                                              
        self.cmd( self.pox, 'forwarding.l2_learning &' )                                               
    def stop( self ):                                                                                  
        "Stop POX"                                                                                     
        self.cmd( 'kill %' + self.pox )                                                                
                                                                                                       
# controllers = { 'poxbridge': POXBridge } 


def waitListening(client, server, port):
    "Wait until server is listening on port"
    if not 'telnet' in client.cmd('which telnet'):
        raise Exception('Could not find telnet')
    cmd = ('sh -c "echo A | telnet -e A %s %s"' %
           (server.IP(), port))
    while 'Connected' not in client.cmd(cmd):
        print('waiting for' + server +
               'to listen on port' + port + '\n')
        sleep(.5)

def progress(t):
    while t > 0:
        print('  %3d seconds left  \r' % (t))
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print('\r\n')

default_dir = '.'

def monitor_qlen(iface, interval_sec = 0.1, fname='%s/qlen.txt' % default_dir):
    """qdisc htb 5: root refcnt 2 r2q 10 default 1 direct_packets_stat 0 direct_qlen 1000
       Sent 108732374 bytes 71875 pkt (dropped 0, overlimits 15535 requeues 0) 
       backlog 0b 0p requeues 0
       qdisc netem 10: parent 5:1 limit 100000
       Sent 108732374 bytes 71875 pkt (dropped 0, overlimits 0 requeues 0) 
       backlog 0b *0p* requeues 0"""
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
    #open('qlen.txt', 'w').write('\n'.join(ret))
    return


def main():
    # topo = FacebookFatTree(4)
    host_number = 4
    topo = StarTopo(host_number)
    print("end create topo")
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, switch=Switch, autoStaticArp=True)
    print("end create net")
    net.start()

    h1 = net.getNodeByName('host_1')
    print(h1.cmd('ping -c 2 10.0.0.2'))
    h1.sendCmd('iperf -s -t 20', printPid=True)

    clients = [net.getNodeByName('host_%d' % (i+1)) for i in xrange(1, host_number)]
    waitListening(clients[0], h1, 5001)

    monitors = []
    # add more switch interface for fat-tree topo
    # may consider using mtr to test ping, -s PACKETSIZE, --psize PACKETSIZE
    monitor = multiprocessing.Process(target=monitor_qlen, args=('s1-eth1', 0.1, '%s/qlen_s1-eth1.txt' % "/home/ubuntu/test/output"))
    monitor.start()
    monitors.append(monitor)

    for i in xrange(1, host_number):
        node_name = 'host_%d' % (i+1)
        cmd = 'iperf -c 10.0.0.1 -t %d -i 1 -Z dctcp > %s/iperf_%s.txt' % (5, "/home/ubuntu/test/output", node_name)
        h = net.getNodeByName(node_name)
        h.sendCmd(cmd)
    
    progress(5)
    for monitor in monitors:
        monitor.terminate()

    net.getNodeByName('host_1').pexec("/sbin/ifconfig > %s/ifconfig.txt" % "/home/ubuntu/test/output", shell=True)
    for i in xrange(0, host_number):
        net.getNodeByName('host_%d' % (i + 1)).waitOutput()
        print('host_%d finished' % (i + 1))
    net.stop()
    # monitors = []

    # monitor = multiprocessing.Process(target=monitor_cpu, args=('%s/cpu.txt' % args.dir,))
    # monitor.start()
    # monitors.append(monitor)

    # monitor = multiprocessing.Process(target=monitor_qlen, args=('s1-eth1', 0.01, '%s/qlen_s1-eth1.txt' % (args.dir)))
    # monitor.start()
    # monitors.append(monitor)

    # monitor = multiprocessing.Process(target=monitor_devs_ng, args=('%s/txrate.txt' % args.dir, 0.01))
    # monitor.start()
    # monitors.append(monitor)
    # Popen("rmmod tcp_probe; modprobe tcp_probe; cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.dir, shell=True)
    # #CLI(net)

    # for i in xrange(1, args.n):
    #     node_name = 'host_%d' % (i+1)
    #     if args.udp:
    #         cmd = 'iperf -c 10.0.0.1 -t %d -i 1 -u -b %sM > %s/iperf_%s.txt' % (seconds, args.bw, args.dir, node_name)
    #     else:
    #         cmd = 'iperf -c 10.0.0.1 -t %d -i 1 -Z reno > %s/iperf_%s.txt' % (seconds, args.dir, node_name)
    #     h = net.getNodeByName(node_name)
    #     h.sendCmd(cmd)
    # net.stop()

    # net.getNodeByName('h2').popen('/bin/ping 10.0.0.1 > %s/ping.txt' % args.dir,
    #     shell=True)
    # if args.tcpdump:
    # for i in xrange(args.n):
    #     node_name = 'h%d' % (i+1)
    #     net.getNodeByName(node_name).popen('tcpdump -ni %s-eth0 -s0 -w \
    #         %s/%s_tcpdump.pcap' % (node_name, args.dir, node_name), 
    #         shell=True)
    # progress(seconds)
    # for monitor in monitors:
    #     monitor.terminate()

    # net.getNodeByName('h1').pexec("/bin/netstat -s > %s/netstat.txt" %
    #     args.dir, shell=True)
    # net.getNodeByName('h1').pexec("/sbin/ifconfig > %s/ifconfig.txt" %
    #     args.dir, shell=True)
    # net.getNodeByName('h1').pexec("/sbin/tc -s qdisc > %s/tc-stats.txt" %
    #         args.dir, shell=True)
    # net.stop()
    # disable_dctcp()
    # disable_tcp_ecn()
    # Popen("killall -9 cat ping top bwm-ng", shell=True).wait()
if __name__ == '__main__':
    main()












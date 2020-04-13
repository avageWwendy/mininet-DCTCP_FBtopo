from mininet.topo import Topo



HOST_PER_NODE       = 2
LINK_BW             = 10
LINK_DELAY          = '.001ms'
NUM_FRABRIC_SWITCH  = 4
NUM_SPINE_SWITCH    = NUM_FRABRIC_SWITCH * NUM_FRABRIC_SWITCH
SWITCH_TYPE         = 'ovsk'

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
        for i in range(len(spine_switches)):
            spine = spine_switches[i]
            idx_offset = (i // NUM_FRABRIC_SWITCH) * num_TOR
            for j in range(num_TOR):
                self.addLink(spine, edge_switches[idx_offset+j], bw=LINK_BW, delay=LINK_DELAY)
        print("finished creating spine-edge")

        # add links from edge to rack
        for i in range(len(edge_switches)):
            edge = edge_switches[i]
            idx_offset = (i % num_TOR) * num_TOR
            for j in range(num_TOR):
                self.addLink(edge, rack_switches[idx_offset+j], bw=LINK_BW, delay=LINK_DELAY)
        print("finished creating edge-rack")

        # add hosts to rack
        h = 0
        for rack in rack_switches:
            for i in range(HOST_PER_NODE):
                self.addLink(rack, self.addHost("host_%s" % str(h)))
                h += 1
        print("finished creating hosts")

topos = { 'facebook_fattree': ( lambda: FacebookFatTree(8) ) }



# Source: https://github.com/mininet/mininet/wiki/Introduction-to-Mininet#creating                                                                                                                                                                                   

from mininet.net import Mininet
from mininet.node import Controller
from mininet.log import setLogLevel

import os

class POXBridge( Controller ):                                                                         
    "Custom Controller class to invoke POX forwarding.l2_learning"                                     
    def start( self ):                                                                                 
        "Start POX learning switch"                                                                    
        self.pox = '%s/pox/pox.py' % os.environ[ 'HOME' ]                                              
        self.cmd( self.pox, 'forwarding.l2_learning &' )                                               
    def stop( self ):                                                                                  
        "Stop POX"                                                                                     
        self.cmd( 'kill %' + self.pox )                                                                
                                                                                                       
controllers = { 'poxbridge': POXBridge } 

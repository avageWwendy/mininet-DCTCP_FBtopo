from mininet.topo import Topo
k = 2

# reference: https://www.cs.cornell.edu/courses/cs5413/2014fa/lectures/08-fattree.pdf

class FatTree(Topo):
    def __init__(self,k):        
        # Initialize topology
        Topo.__init__(self)

        # create elements
        aggr_switch = []
        for i in range(k*k//2):
            aggr_switch.append(self.addSwitch("aggr_%s" % str(i)))
        edge_switch = []
        for i in range(k*k//2):
            edge_switch.append(self.addSwitch("edge_%s" % str(i)))
        core_switch = []
        for i in range(k):
            core_switch.append(self.addSwitch("core_%s" % str(i)))
        
        print("finished creating elements")

        # add links from core to aggregation
        for c in range(k):
            core = core_switch[c]
            # which aggr should be connected to
            aggr_offset = c / 2
            for a in range(k):
                self.addLink(core, aggr_switch[k * a // 2 + aggr_offset])
        
        print("finished creating core-aggr")
        
        # add links from aggregation to edge
        for p in range(k):
            for a in range(int(k/2)):
                # print(p * k / 2 + a)
                aggr = aggr_switch[p * k // 2 + a]
                for e in range(int(k/2)):
                    edge = edge_switch[p * k // 2 + e]
                    self.addLink(aggr, edge)
        
        print("finished creating aggr-edge")

        # add host to edges
        h = 0
        for edge in edge_switch:
            for i in range(k//2):
                self.addLink(edge, self.addHost("host_%s" % str(h)))
                h += 1
        
        print("finished creating hosts")


topos = { 'fattree': ( lambda: FatTree(k) ) }

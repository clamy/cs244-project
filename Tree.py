#!/usr/bin/python

"CS244 Assignment 1: Parking Lot"

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, output
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI

from time import sleep, time
from multiprocessing import Process
from subprocess import Popen
#import termcolor as T
import argparse

import sys
import os
from util.monitor import monitor_devs_ng

def cprint(s, color, cr=True):
    """Print in color
       s: string to print
       color: color to use"""
    if cr:
        print T.colored(s, color)
    else:
        print T.colored(s, color),

parser = argparse.ArgumentParser(description="Parking lot tests")
parser.add_argument('--bw', '-b',
                    type=float,
                    help="Bandwidth of network links",
                    required=True)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    default="results")

#parser.add_argument('-n',
                    #type=int,
                    #help=("Number of senders in the parking lot topo."
                    #"Must be >= 1"),
                    #required=True)

parser.add_argument('--cli', '-c',
                    action='store_true',
                    help='Run CLI for topology debugging purposes')

parser.add_argument('--time', '-t',
                    dest="time",
                    type=int,
                    help="Duration of the experiment.",
                    default=60)

# Expt parameters
args = parser.parse_args()

if not os.path.exists(args.dir):
    os.makedirs(args.dir)

lg.setLogLevel('info')

# Topology to be instantiated in Mininet
class ParkingLotTopo(Topo):
    "Parking Lot Topology"

    def __init__(self, n=1, cpu=.1, bw=10, delay=None,
                 max_queue_size=None, **params):
        """Parking lot topology with one receiver
           and n clients.
           n: number of clients
           cpu: system fraction for each host
           bw: link bandwidth in Mb/s
           delay: link delay (e.g. 10ms)"""

        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        hconfig = {'cpu': cpu}
        lconfig = {'bw': bw, 'delay': delay,'max_queue_size': max_queue_size }

        # Create the actual topology
        #receiver = self.add_host('receiver')

        # Switch ports 1:uplink 2:hostlink 3:downlink
        #uplink, hostlink, downlink = 1, 2, 3

        # The following template code creates a parking lot topology
        # for N = 1
        # TODO: Replace the template code to create a parking lot topology for any arbitrary N (>= 1)
        # Begin: Template code

        root_switch = self.add_switch('s0')

        #add five child switches and to each of them connect four hosts

        #for s in range(1,6):
        for s in range(1,5):
            switch = self.add_switch('s%s' % s)
            self.add_link(root_switch, switch, port1=s,port2=0, **lconfig )
            for h in range(1,4):
                host = self.add_host('h%s' % (((s-1)*3) + h), **hconfig )
                self.add_link(host, switch,port1=0, port2=h, **lconfig )

def waitListening(client, server, port):
    "Wait until server is listening on port"
    if not 'telnet' in client.cmd('which telnet'):
        raise Exception('Could not find telnet')
    cmd = ('sh -c "echo A | telnet -e A %s %s"' %
           (server.IP(), port))
    while 'Connected' not in client.cmd(cmd):
        output('waiting for', server,
               'to listen on port', port, '\n')
        sleep(.5)

def progress(t):
    while t > 0:
        cprint('  %3d seconds left  \r' % (t), 'cyan', cr=False)
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print

def start_tcpprobe():
    os.system("rmmod tcp_probe &>/dev/null; modprobe tcp_probe;")
    Popen("cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.dir, shell=True)

def stop_tcpprobe():
    os.system("killall -9 cat; rmmod tcp_probe &>/dev/null;")

def run_parkinglot_expt(net):
    "Run experiment"

    seconds = args.time

    # Start the bandwidth and cwnd monitors in the background
    monitor = Process(target=monitor_devs_ng, 
            args=('%s/bwm.txt' % args.dir, 1.0))
    monitor.start()
    start_tcpprobe()

    start_reception(net)
    start_senders(net)
    stop_receivers(net)

    # Shut down monitors
    monitor.terminate()
    stop_tcpprobe()

def stop_receivers(net):
    host_list = net.hosts
    for x in xrange(1, len(host_list) + 1):
        receiver_name = "h" + str(x)
        recvr = net.getNodeByName(receiver_name)
        recvr.cmd('kill %iperf')

#TODO: configure receivers to be same as senders whether 20 or 12
def start_reception(net):
    host_list = net.hosts
    for x in xrange(1, len(host_list) + 1):
        receiver_name = "h" + str(x)
        recvr = net.getNodeByName(receiver_name)
        port = 5001
        recvr.cmd('iperf -s -p', port,'> %s/iperf_server.txt' % args.dir, '&')
        
        #sender1 = net.getNodeByName('h1')
        #waitListening(sender1, recvr, port)

def start_senders(net):
    # Seconds to run iperf; keep this very high
    seconds = 3600
    #file_size = 50000000000
    file_size = 5000000
    #pass
    host_list = net.hosts
    for x in xrange(1, len(host_list)+ 1):
        for y in xrange(1, len(host_list)+ 1):
            senderName = "h" + str(x)
            cur_sender = net.getNodeByName(senderName)

            if (x != y):
                receiverName = "h" + str(y)
                receiver = net.getNodeByName(receiverName)
                rcv_ip = receiver.IP()
                output_file = "iperf_server.txt"
                iperfArgs = 'iperf -c %s -p %s -n %d -i 1 -yc > %s/iperf_%s.txt &' % (rcv_ip, 5001,file_size, args.dir, senderName)
                cur_sender.cmd(iperfArgs)

    print('Please wait until the experiment is complete...')            
    sleep (args.time)
    #for x in xrange(1, len(host_list)+1):
    #senderName = "h" + str(x)
    #cur_sender = net.getNodeByName(senderName)
    #cur_sender.waitOutput()

def check_prereqs():
    "Check for necessary programs"
    prereqs = ['telnet', 'bwm-ng', 'iperf', 'ping']
    for p in prereqs:
        if not quietRun('which ' + p):
            raise Exception((
                'Could not find %s - make sure that it is '
                'installed and in your $PATH') % p)

def main():
    "Create and run experiment"
    start = time()

    topo = ParkingLotTopo()

    host = custom(CPULimitedHost, cpu=.15)  # 15% of system bandwidth

    link = custom(TCLink, bw=args.bw, delay='1ms',
                  max_queue_size=200)
    #link = custom(TCLink, bw=args.bw, delay='1ms',
                  #max_queue_size=2000)
    
    net = Mininet(topo=topo, host=host, link=link)

    net.start()

    #cprint("*** Dumping network connections:", "green")
    dumpNetConnections(net)

    #cprint("*** Testing connectivity", "blue")

    #net.pingAll()

    if args.cli:
        # Run CLI instead of experiment
        CLI(net)
    else:
        #cprint("*** Running experiment", "magenta")
        run_parkinglot_expt(net)

    net.stop()
    end = time()
    os.system("killall -9 bwm-ng")
    #cprint("Experiment took %.3f seconds" % (end - start), "yellow")

if __name__ == '__main__':
    check_prereqs()
    main()


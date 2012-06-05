#!/usr/bin/python

"CS244 Assignment 1: Parking Lot"

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, output
from mininet.node import CPULimitedHost, RemoteController, Controller
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

parser.add_argument('-n',
                    type=int,
                    help=("Number of senders in the parking lot topo."
                    "Must be >= 1"),
                    required=True)

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
class DCellTopo(Topo):
    "DCell Topology k = 2, n = 4"

    def __init__(self, n=1, cpu=.1, bw=1000, delay=None,
                 max_queue_size=None, **params):

        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        hconfig = {'cpu': cpu}
        lconfig = {'bw': bw, 'delay': delay,
                   'max_queue_size': max_queue_size }

        # Create the actual topology
        # Creats each sub-module Dcell0
        for i in range(1, 6):
            s = self.add_switch(name = 's'+str(i))
            for j in range(1, 5):
                h = self.add_host('h'+str(i)+str(j), **hconfig)
                s_h = self.add_switch(name = 's'+str(i)+str(j))
                self.add_link(h, s_h, port1=0, port2=0, **lconfig)
                self.add_link(s_h, s, port1=1, port2=j, **lconfig)
                
        # Creats the connection between sub-modules        
        for i in range(1, 5):
            for j in range(i, 5):
                self.add_link('s'+str(i)+str(j), 's'+str(j+1)+str(i), port1=2, port2=2, **lconfig)


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


def run_DCell_data(net):
    "Run experiment"

    seconds = args.time

    # Start the bandwidth and cwnd monitors in the background
    monitor = Process(target=monitor_devs_ng, 
            args=('%s/bwm.txt' % args.dir, 1.0))
    monitor.start()
    start_tcpprobe()

    # Get receiver and clients
    #recvr = net.getNodeByName('receiver')
    #sender1 = net.getNodeByName('h1')

    # Start the receiver
    port = 5001

    data_size = 5000000
    for i in range(1, 6):        
        for j in range(1, 5):
            h = net.getNodeByName('h'+str(i)+str(j))            
            h.cmd('iperf -s -p', port,
              '> %s/iperf_server.txt' % args.dir, '&')
    
    # Send the commands
    for i in range(1, 5):        
        for j in range(1, 4):
            sender = net.getNodeByName('h'+str(i)+str(j))
            for k in range(1, 5):        
                for l in range(1, 4):
                    if k!=i or l!=j :
                        receiver = net.getNodeByName('h'+str(k)+str(l))
                        ip =  receiver.IP()        
                        sender.cmd('iperf -c %s -p %s -n %d -i 1 -yc > %s/iperf_%s.txt &' % (ip, 5001, data_size, args.dir,'h'+str(i)+str(j)))
                        
    print('Please wait until the experiment is complete...')    
    sleep(args.time)

    for i in range(1,6):
        for j in range(1,5):
            recvr = net.getNodeByName('h'+str(i)+str(j))
            recvr.cmd('kill %iperf')

    # Shut down monitors
    monitor.terminate()
    stop_tcpprobe()    

def run_DCell_link_node_failure(net):
    "Run link/node failure experiment"

    print('Please wait until the experiment is complete...')    
    seconds = args.time

    # Start the bandwidth and cwnd monitors in the background
    monitor = Process(target=monitor_devs_ng, 
            args=('%s/bwm.txt' % args.dir, 1.0))
    monitor.start()
    start_tcpprobe()

    # Get receiver and clients
    recvr = net.getNodeByName('h54')
    sender = net.getNodeByName('h11')

    # Start the receiver
    port = 5001
    recvr.cmd('iperf -s -p', port,'> %s/iperf_server.txt' % args.dir, '&')

    waitListening(sender, recvr, port)
    
    # Send the commands
    sender.sendCmd('iperf -c %s -p %s -t %d -i 1 -yc > %s/iperf_%s.txt' % (recvr.IP(), 5001, seconds, args.dir,'h11'))#
        
    sleep(34)
    print '***Link Down!...'
    net.configLinkStatus('s14','s51','down')

    sleep(8)
    print '***Link Up Again!...'
    net.configLinkStatus('s14','s51','up')
    
    sleep(62)
    print '***Switch Down!...'
    toKill = net.getNodeByName('s14')
    toKill.stop();

    # Waint for it to finish    
    sender.waitOutput()#

    recvr.cmd('kill %iperf')#

    # Shut down monitors
    monitor.terminate()
    stop_tcpprobe()

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

    topo = DCellTopo()

    host = custom(CPULimitedHost, cpu=.15)  # 15% of system bandwidth
    link = custom(TCLink, bw=args.bw, delay='1ms',
                  max_queue_size=20000)
    
    net = Mininet(topo=topo, host=host, link=link, controller=RemoteController, autoStaticArp=True)

    
    for i in range(1, 6):
        for j in range(1, 5):
            h = net.getNodeByName('h'+str(i)+str(j))
            h.setMAC('00:0'+str(i)+':0'+str(j)+':00:00:00')
            h.setIP('10.0.'+str(i)+'.'+str(j))
                
    net.start()

    print "*** Dumping network connections:"
    dumpNetConnections(net)
    
    print "***Run Controller."
    c = raw_input("***Wait untill all switches are connected to controller then press Return...")

   # print "*** Testing connectivity"
   # net.pingAll()
    
    if args.n == 1:
        print "***Runing the link-node failure experiment"
        run_DCell_link_node_failure(net)
    elif args.n == 2:    
        print "***Runing the data transmission experiment"
        run_DCell_data(net)

    net.stop()
    end = time()
    os.system("killall -9 bwm-ng")

if __name__ == '__main__':
    check_prereqs()
    main()


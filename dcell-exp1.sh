#!/bin/bash

# Exit on any failure
set -e

# Check for uninitialized variables
set -o nounset

ctrlc() {
	killall -9 python
	mn -c
	exit
}

trap ctrlc SIGINT

start=`date`
exptid=`date +%b%d-%H:%M`
rootdir=DCell-Exp1-$exptid
bw=100

# Note: you need to make sure you report the results
# for the correct port!
# In this example, we are assuming that each
# client is connected to port 2 on its switch.

dir=$rootdir/data
python DCell.py --bw $bw\
     --dir $dir\
     -t 180\
     -n 1
python util/plot_rate.py --rx\
     --maxy $bw\
     --xlabel 'Time (s)'\
     --ylabel 'Rate (Mbps)'\
     -i 's54-eth1'\
     -f $dir/bwm.txt\
     -o $rootdir/rate.png

echo "Started at" $start
echo "Ended at" `date`
echo "Output saved to $rootdir"

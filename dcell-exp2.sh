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
 
treerootdir=Tree-$exptid
#treerootdir='Tree-Jun04-06:45'
dcellrootdir=DCell-Exp2-$exptid
#dcellrootdir='DCell-Exp2-Jun04-06:45'
combinedresultsdir=plotresults-$exptid
mkdir $combinedresultsdir
   
bw=1
 
 
dir1=$dcellrootdir/data
python DCell.py --bw $bw\
     --dir $dir1\
     -t 500\
     -n 2

echo "Please terminate the controller using Cotrrol-D, then press Return..."
read c

dir2=$treerootdir/data
python Tree.py --bw $bw\
     --dir $dir2\
     -t 1000\



python util/plot_rate_ag_both.py --rx \
    --maxy $bw \
    --xlabel 'Time (s)' \
    --ylabel 'Rate (Mbps)' \
    -i 's.*-eth0' \
    -f $dir2/bwm.txt \
    -d $dir1/bwm.txt \
    -o $combinedresultsdir/rate_ag.png
 
 
echo "Started at" $start
echo "Ended at" `date`
echo "Output saved to $combinedresultsdir"
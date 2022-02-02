#! /bin/sh

if [ $# -ne 2 ]
then
  echo "usage: $0 <data-dir> <static-gtfs-url>"
  exit 1
fi

DATA_DIR=$1
GTFS_URL=$2

for i in `ls $DATA_DIR | grep "^202*"`
do
  echo i: $i
  LOG=~/tmp/$i-log.txt
  python3 run-archived-trip.py -d $DATA_DIR/$i/updates.txt -c ~/tmp/tuff -u $GTFS_URL > $LOG
  echo "expected: "` head -1 $DATA_DIR/$i/metadata.txt | sed 's/.*: //'`
  grep "^- trip_id:" $LOG | uniq -c
done

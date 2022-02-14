#! /bin/sh

if [ $# -ne 2 ]
then
  echo "usage: $0 <data-dir> <static-gtfs-url>"
  exit 1
fi

DATA_DIR=$1
GTFS_URL=$2

TIME_STAMP=`date +"%Y-%m-%d-%H-%M"`
RESULT_FILE=$DATA_DIR/results-${TIME_STAMP}.txt
STATS_FILE=~/data/scripts/ti-scores-${TIME_STAMP}.txt

# sorting is critical to not constantly reload static data
DATA_FILES=`find $DATA_DIR -name updates.txt -print | sort`
echo DATA_FILES: $DATA_FILES

time python3 run-archived-trip.py -c ~/tmp/tuff -u $GTFS_URL $DATA_FILES > log.txt

cat /dev/null > $RESULT_FILE

for i in `ls $DATA_DIR | grep "^202*"`
do
  echo i: $i >> $RESULT_FILE
  LOG=~/tmp/$i-log.txt
  echo "expected: "` head -1 $DATA_DIR/$i/metadata.txt | sed 's/.*: //'` >> $RESULT_FILE
  grep "^- trip_id:" $LOG | uniq -c >> $RESULT_FILE
done

python3 inference-stats.py $RESULT_FILE > $STATS_FILE
tail -1 $STATS_FILE

osascript -e 'display alert "Batch run complete"'

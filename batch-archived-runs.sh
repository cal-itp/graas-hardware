#! /bin/sh

if [ $# -ne 4 ]
then
  echo "usage: $0 <data-dir> <output-dir> <gtfs-cache-dir> <static-gtfs-url>"
  echo "  <data-dir>: where to find training data, e.g. $GRASS_REPO/data/trip-inference-training/included"
  echo "  <output-dir>: where to put output data, e.g. ~/tmp"
  echo "  <gtfs-cache-dir>: where to cache GTFS data. e.g. ~/tmp/gtfs-cache"
  echo "  <static-gtfs-url>: live GTFS URL or archived file, e.g. $GRASS_REPO/data/trip-inference-training/gtfs-archive/2022-02-14-tcrta-gtfs.zip"
  exit 1
fi

DATA_DIR=$1
OUTPUT_DIR=$2
CACHE_DIR=$3
GTFS_URL=$4

TIME_STAMP=`date +"%Y-%m-%d-%H-%M"`
RESULT_FILE=$OUTPUT_DIR/results-${TIME_STAMP}.txt
STATS_FILE=$OUTPUT_DIR/ti-scores-${TIME_STAMP}.txt

# sorting is critical to not constantly reload static data
DATA_FILES=`find $DATA_DIR -name updates.txt -print | sort`
echo DATA_FILES: $DATA_FILES

rm -f $OUTPUT_DIR/202*-log.txt
time python3 run-archived-trip.py -c $CACHE_DIR -u $GTFS_URL $DATA_FILES > $OUTPUT_DIR/log.txt

echo RESULT_FILE: $RESULT_FILE
cat /dev/null > $RESULT_FILE

for i in `ls $DATA_DIR/trip-inference-training/included/ | grep "^202*"`
do
  echo i: $i >> $RESULT_FILE
  LOG=$OUTPUT_DIR/$i-log.txt
  echo "expected: "` head -1 $DATA_DIR/trip-inference-training/included/$i/metadata.txt | sed 's/.*: //'` >> $RESULT_FILE
  grep "^- trip_id:" $LOG | uniq -c >> $RESULT_FILE
done

python3 inference-stats.py $RESULT_FILE > $STATS_FILE
tail -1 $STATS_FILE

if [[ $OSTYPE == "darwin"* ]]
then
  osascript -e 'say "calculation complete, your move!" using "Zarvox"'
  osascript -e 'display alert "Batch job complete!"'
fi

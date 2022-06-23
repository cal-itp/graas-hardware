"""
TIME_STAMP=`date +"%Y-%m-%d-%H-%M"`
RESULT_FILE=$OUTPUT_DIR/results-${TIME_STAMP}.txt
STATS_FILE=$OUTPUT_DIR/ti-scores-${TIME_STAMP}.txt

# sorting is critical to not constantly reload static data
DATA_FILES=`find $DATA_DIR -name updates.txt -print | sort`
echo DATA_FILES: $DATA_FILES
echo STATS_FILE: $STATS_FILE


rm -f $OUTPUT_DIR/202*-log.txt
# run with '-b' to simulate bulk assignment
# run without '-b' to not simulate bulk mode (aka hard mode)
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
SCORE=`tail -1 $STATS_FILE | awk '{print $2}'`
echo "score: $SCORE"

if [[ $OSTYPE == "darwin"* ]]
then
  osascript -e 'say "calculation complete, your move!" using "Zarvox"'
  osascript -e "display alert \"Batch job complete, score: $SCORE\""
fi
"""

from datetime import datetime
import os
import glob
import sys
import time
import util

import inference_stats
import run_archived_trip

def main(data_dir, output_dir, gtfs_cache_dir, static_gtfs_url, simulate_block_assignment):
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
    result_file = f'{output_dir}/results-{timestamp}.txt'
    stats_file = f'{output_dir}/ti-scores-{timestamp}.txt'

    data_files = []

    for dirpath,_,filenames in os.walk(data_dir):
            for f in filenames:
                if f == 'updates.txt':
                    data_files.append(os.path.abspath(os.path.join(dirpath, f)))

    data_files.sort()

    print(f'- data_files: {data_files}')
    print(f'- stats_file: {stats_file}')

    files = glob.glob(f'{output_dir}/202*-log.txt')
    for f in files:
        #print(f'-- f: {f}')
        os.remove(f)

    stdout_save = sys.stdout
    log_file = f'{output_dir}/log.txt'
    print(f'- log_file: {log_file}')
    sys.stdout = open(log_file, 'w')
    then = int(time.time())
    run_archived_trip.main(data_files, gtfs_cache_dir, output_dir, static_gtfs_url, simulate_block_assignment)
    sys.stdout.close()
    sys.stdout = stdout_save
    print(f'+ elapsed time: {int(time.time()) - then} seconds')
    print(f'- result_file: {result_file}')

    with open(result_file, 'w') as f:
        files = glob.glob(f'{data_dir}/trip-inference-training/included/202*')
        for i in files:
            #print(f'-- i: {i}')
            si = i.rfind('/')
            rel_i = i[si + 1:]
            #print(f'-- rel_i: {rel_i}')
            f.write(f'i: {rel_i}\n')
            log = f'{output_dir}/{rel_i}-log.txt'
            metadata = f'{i}/metadata.txt'
            expected_trip_id = None
            with open(metadata) as mf:
                s = mf.readline().strip()
                n = s.find(': ')
                expected_trip_id = s[n + 2:]
            f.write(f'expected: {expected_trip_id}\n')
            trip_ids = {}
            with open(log) as lf:
                for line in lf:
                    s = line.strip()
                    if len(s) == 0:
                        continue
                    if s.startswith('- trip_id:'):
                        if s in trip_ids:
                            trip_ids[s] = trip_ids[s] + 1
                        else:
                            trip_ids[s] = 1
            for k in trip_ids.keys():
                f.write(f'{trip_ids[k]} - {k}\n')

    sys.stdout = open(stats_file, 'w')
    inference_stats.main(result_file)
    sys.stdout.close()
    sys.stdout = stdout_save

    line = ''
    with open(stats_file) as f:
        for line in f:
            line = line.strip()
    score = line.split(' ')[1]
    print(f'score: {score}')

if __name__ == '__main__':
    data_dir = None
    output_dir = None
    gtfs_cache_dir = None
    static_gtfs_url = None
    simulate_block_assignment = False

    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '-d' and i < len(sys.argv) - 1:
            i += 1
            data_dir = sys.argv[i]

        if sys.argv[i] == '-o' and i < len(sys.argv) - 1:
            i += 1
            output_dir = sys.argv[i]

        if sys.argv[i] == '-g' and i < len(sys.argv) - 1:
            i += 1
            gtfs_cache_dir = sys.argv[i]

        if sys.argv[i] == '-s' and i < len(sys.argv) - 1:
            i += 1
            static_gtfs_url = sys.argv[i]

        if sys.argv[i] == '-b':
            simulate_block_assignment = True

    if data_dir is None or output_dir is None or gtfs_cache_dir is None or static_gtfs_url is None:
        util.debug(f'* usage: {sys.argv[0]} -d <data-dir> -o <output-dir> - g <gtfs-cache-dir> - s <static-gtfs-url> [-b]')
        util.debug(f'  -b: simulate block assignment')
        util.debug(f'  <data-dir>: where to find training data, e.g. $GRASS_REPO/data/trip-inference-training/included')
        util.debug(f'  <output-dir>: where to put output data, e.g. ~/tmp')
        util.debug(f'  <gtfs-cache-dir>: where to cache GTFS data. e.g. ~/tmp/gtfs-cache')
        util.debug(f'  <static-gtfs-url>: live GTFS URL or archived file, e.g. $GRASS_REPO/data/trip-inference-training/gtfs-archive/2022-02-14-tcrta-gtfs.zip')

        exit(1)

    main(data_dir, output_dir, gtfs_cache_dir, static_gtfs_url, simulate_block_assignment)

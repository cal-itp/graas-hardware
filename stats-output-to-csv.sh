#! /bin/sh

if [ $# -ne 1 ]
then
  echo "usage: $0 <input-file>"
  exit 1
fi

INPUT_FILE=$1
cat $INPUT_FILE | grep -v '^---' | grep -v 'avg:' | sed 's/: /,/' | sed 's/%//'

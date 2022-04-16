#! /bin/sh

# copy compressed logs to desktop with:
# scp -P 24872 pi@3.tcp.ngrok.io:/home/pi/logs/logs.tar.gz .

cd ~/logs
rm -f processed-*.txt

for i in `ls almanor-*.txt`
do
  echo $i
  egrep "current location| \- trip_id" $i > processed-$i
done

tar cf logs.tar processed-almanor-6-22-04-*
gzip logs.tar


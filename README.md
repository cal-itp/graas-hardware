
GRaaS Hardware
===============
Satellite repository to the [mothership](https://github.com/cal-itp/graas.git). Software that runs on the GRaaS hardware is kept separately here to have repo size remain small for clients who will pull over limited bandwidth nextworks.

Run trip inference against training data: `./batch-archived-runs.sh $MAIN_GRAAS_REPO/data <static-gtfs-agency-cache> <static-gtfs-url|static-gtfs-local-file>`
- `static-gtfs-agency-cache`: a folder to write agency cache files to
- `static-gtfs-url`: URL to agency static GTFS data
- `static-gtfs-local-file`: local copy of agency GTFS data

Generate graphs from trip inference training runs:
- identify stats file from run (tool will say: `STATS_FILE: <path>`)
- convert stats file to CSV with: `stats-output-to-csv.sh <path-to-stats-file> > ~/tmp/chart.csv`
- go to https://chart-studio.plotly.com/create/#/
- press import button and upload generated chart.csv file
- press `+ Trace` button
- choose `Bar` type
- set `x` dropdown to name of first column from spreadsheet on top right
- set `y` dropdown to name of second column from spreadsheet on top right
- set bar color under `Style->Traces` to e.g. `#B635C7`
- admire graph :)


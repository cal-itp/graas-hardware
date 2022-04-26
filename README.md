
GRaaS Hardware
===============
Satellite repository to the [mothership](https://github.com/cal-itp/graas.git). Software that runs on the GRaaS hardware is kept separately here to have repo size remain small for clients who will pull over limited bandwidth nextworks.

Run trip inference against training data: `./batch-archived-runs.sh $MAIN_GRAAS_REP/data <static-gtfs-agency-cache> <static-gtfs-url|static-gtfs-local-file>`
- `static-gtfs-agency-cache`: a folder to write agency cache files to
- `static-gtfs-url`: URL to agency static GTFS data
- `static-gtfs-local-file`: local copy of agency GTFS data

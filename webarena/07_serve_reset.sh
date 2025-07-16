#!/bin/bash

# stop if any error occur
set -e

source 00_vars.sh

# activate venv with flask
source .venv/bin/activate

cd reset_server/
python server.py --port ${RESET_PORT} 2>&1 | tee -a server.log

#!/bin/bash

# stop if any error occur
set -e

source 00_vars.sh

# activate venv with flask
source .venv/bin/activate

cd task_viewer/
python server.py 2>&1 | tee -a server.log

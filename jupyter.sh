#!/bin/bash
set -x

jupyter lab --notebook-dir=/home/scitech/shared-data --port=8888 --no-browser --ip=0.0.0.0 --ServerApp.token='' --allow-root &



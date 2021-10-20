#!/bin/bash

IPYNB="$1"
basename_ipynb="${IPYNB%.*}"

ln -s /usr/local/etc/slurm.conf /etc/opt/slurm/slurm.conf
condor_master > /dev/null 2>&1

jupyter nbconvert --to script "$IPYNB"

mv "${basename_ipynb}".py "${basename_ipynb}".ipy

ipython "${basename_ipynb}".ipy

rm "${basename_ipynb}".ipy

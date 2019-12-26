#!/bin/bash

NUMCORES=`grep -c ^processor /proc/cpuinfo`
SUBSEQUENCE_EVALS=`grep "SUBSEQUENCE_EVALS" lib/common.py | awk '{print $3}'`
PARALLELISM=$(( ${NUMCORES} < ${SUBSEQUENCE_EVALS} ? ${NUMCORES} : ${SUBSEQUENCE_EVALS} ))

echo "Starting ${PARALLELISM} tasks..."

for ((i = 0; i < ${PARALLELISM}; i++)); do
    PYTHONPATH=. lib/hyperopt-mongo-worker --mongo=localhost:45555/db \
                                           --exp-key=tpprof1 \
                                           --poll-interval=0.1 \
                                           --workdir=/tmp &
done

wait

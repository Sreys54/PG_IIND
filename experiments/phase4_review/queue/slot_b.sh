#!/bin/bash
# Week 8 review compute queue, slot B (resumable steps; run from the repo root).
export PYTHONPATH=.
L=experiments/phase4_review/queue
python scripts/review_C4_capacity.py --part threshold --arm PS --ports 8 > $L/log_thr_ps_p8.txt 2>&1
python scripts/review_C4_capacity.py --part threshold --arm PS --ports 10 > $L/log_thr_ps_p10.txt 2>&1
python scripts/review_C4_capacity.py --part grid --worker 1 --workers 2 > $L/log_grid_w1.txt 2>&1
python scripts/review_C5_voltage.py --worker 1 --workers 2 > $L/log_c5_w1.txt 2>&1
for d in d1 d2 d3; do python scripts/review_D_sensitivities.py --part $d --worker 1 --workers 2 > $L/log_${d}_w1.txt 2>&1; done
echo done > $L/slot_b.done

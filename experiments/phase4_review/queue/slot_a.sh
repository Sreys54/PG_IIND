#!/bin/bash
# Week 8 review compute queue, slot A (resumable steps; run from the repo root).
export PYTHONPATH=.
L=experiments/phase4_review/queue
python scripts/review_C4_capacity.py --part threshold --arm RR-TA --ports 8 > $L/log_thr_rrta_p8.txt 2>&1
python scripts/review_C4_capacity.py --part threshold --arm RR-TA --ports 10 > $L/log_thr_rrta_p10.txt 2>&1
python scripts/review_C4_capacity.py --part grid --worker 0 --workers 2 > $L/log_grid_w0.txt 2>&1
python scripts/review_C5_voltage.py --worker 0 --workers 2 > $L/log_c5_w0.txt 2>&1
for d in d1 d2 d3; do python scripts/review_D_sensitivities.py --part $d --worker 0 --workers 2 > $L/log_${d}_w0.txt 2>&1; done
echo done > $L/slot_a.done

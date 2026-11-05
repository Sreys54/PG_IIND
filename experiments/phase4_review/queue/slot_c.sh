#!/bin/bash
# Follow-up queue (run after slots A and B finish): $1 = worker index 0/1.
export PYTHONPATH=.
L=experiments/phase4_review/queue
w=$1
python scripts/review_C5_voltage.py --worker $w --workers 2 > $L/log_c5b_w$w.txt 2>&1
python scripts/review_D_sensitivities.py --part d1 --worker $w --workers 2 > $L/log_d1b_w$w.txt 2>&1
python scripts/review_C4_capacity.py --part grid --worker $w --workers 2 > $L/log_gridb_w$w.txt 2>&1
if [ "$w" = "0" ]; then arm=RR-TA; else arm=PS; fi
python scripts/review_C4_capacity.py --part threshold --arm $arm --ports 8 --energy-scale-file experiments/phase4_review/D/d3_energy_scale.txt > $L/log_thr_d3_$arm.txt 2>&1
echo done > $L/slot_c_w$w.done

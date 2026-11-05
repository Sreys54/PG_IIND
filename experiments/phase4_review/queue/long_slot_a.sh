#!/bin/bash
# Week 8 C3 long-budget sensitivity, slot A: seed 100, then seed 102 (config_safe doc long_budget_sensitivity).
cd "$(dirname "$0")/../../.."
export PYTHONPATH=.
for s in 100 102; do
  python scripts/train_td3_safe.py --seed $s --deadline 2026-11-05T23:59:00-05:00 --price-cache --torch-threads 1 \
    --state service_causal --fixed-budget --max-steps 2000000 --output-root C:/ev2gym_runs/w8_td3_safe_long \
    > C:/ev2gym_runs/w8_td3_safe_long_ts$s.log 2>&1
  echo "seed $s exit $?"
done

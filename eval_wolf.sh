#!/bin/bash

# Evaluate linear with colapse with smaller learning rate 
python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=123 load.run=30 log.test_dir=wolf
python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=445 load.run=31 log.test_dir=wolf
python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=7881 load.run=32 log.test_dir=wolf
python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=1116 load.run=33 log.test_dir=wolf
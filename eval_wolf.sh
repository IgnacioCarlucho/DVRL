#!/bin/bash
#SBATCH --job-name=dvrl_lbf
#SBATCH --cpus-per-task=4
#SBATCH --time=2-24:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --gres=gpu:1

# Evaluate linear with colapse with smaller learning rate 
# python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=123 load.run=20 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=445 load.run=21 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=7881 load.run=22 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=1116 load.run=23 log.test_dir=saved_runs
python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=6673 load.run=24 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=84145 load.run=25 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=9911 load.run=26 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf.yaml seed=1026 load.run=27 log.test_dir=saved_runs

# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=123 load.run=20 log.test_dir=wolf
# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=445 load.run=21 log.test_dir=wolf
# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=7881 load.run=22 log.test_dir=wolf
# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=1116 load.run=23 log.test_dir=wolf
# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=6673 load.run=24 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=84145 load.run=25 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=9911 load.run=26 log.test_dir=saved_runs
# python ./code/ckpt_main.py -p with environment.config_file=wolf_test.yaml seed=1026 load.run=27 log.test_dir=saved_runs


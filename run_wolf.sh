#!/bin/bash
#SBATCH --job-name=dvrl_lbf
#SBATCH --cpus-per-task=4
#SBATCH --time=2-24:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --gres=gpu:1

source activate dvrl

export OMP_NUM_THREADS=1 

# export CUDA_VISIBLE_DEVICES="0"

# python ./code/main.py -p with environment.config_file=wolf.yaml seed=123
# python ./code/main.py -p with environment.config_file=wolf.yaml seed=445
# python ./code/main.py -p with environment.config_file=wolf.yaml seed=7881
# python ./code/main.py -p with environment.config_file=wolf.yaml seed=1116
python ./code/main.py -p with environment.config_file=wolf.yaml seed=6673
# python ./code/main.py -p with environment.config_file=wolf.yaml seed=84145
# python ./code/main.py -p with environment.config_file=wolf.yaml seed=9911
# python ./code/main.py -p with environment.config_file=wolf.yaml seed=1026
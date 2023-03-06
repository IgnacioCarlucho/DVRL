#!/bin/bash
#SBATCH --job-name=dvrl_lbf
#SBATCH --cpus-per-task=4
#SBATCH --time=2-24:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --gres=gpu:1

source activate dvrl

export OMP_NUM_THREADS=1 

# export CUDA_VISIBLE_DEVICES="0"

python ./code/main.py -p with environment.config_file=lbf.yaml

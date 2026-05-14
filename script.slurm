#!/bin/bash
#SBATCH -J voice_clone
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=5
#SBATCH --mem=32G
#SBATCH --time=4:00:00
#SBATCH --output=logs/cloning_%j.out
#SBATCH --error=logs/cloning_%j.err

cd "$SLURM_SUBMIT_DIR"
mkdir -p logs output

module load python/3.10.10

# Aktiveeri virtuaalkeskkond 
source "$HOME/venvs/seedvc/bin/activate"

export PYTHONPATH="$SLURM_SUBMIT_DIR/seed-vc:$PYTHONPATH"

python3 -u "$SLURM_SUBMIT_DIR/cloning.py"

deactivate

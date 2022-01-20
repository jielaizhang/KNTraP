#!/bin/bash

#SBATCH --job-name=red_tmpl_21to25
#SBATCH --output=/fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_21to25.out
#SBATCH --error=/fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_21to25.err

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --time=48:00:00
#SBATCH --mem-per-cpu=4G


echo Slurm Job red_tmpl_21to25 start
echo Job .out is saved at: /fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_21to25.out
echo Job .err is saved at: /fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_21to25.err
echo `date`
SECONDS=0
echo -------- --------
source /fred/oz100/NOAO_archive/KNTraP_Project/src/photpipe/config/DECAMNOAO/YSE/YSE.bash.sourceme
pipeloop.pl -red tmpl 21-25 -redobad
echo -------- --------
echo `date`
duration=$SECONDS
echo Slurm Job red_tmpl_21to25 done in $(($duration / 60)) minutes and $(($duration % 60)) seconds

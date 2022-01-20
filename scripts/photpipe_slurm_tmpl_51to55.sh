#!/bin/bash

#SBATCH --job-name=red_tmpl_51to55
#SBATCH --output=/fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_51to55.out
#SBATCH --error=/fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_51to55.err

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --time=48:00:00
#SBATCH --mem-per-cpu=4G


echo Slurm Job red_tmpl_51to55 start
echo Job .out is saved at: /fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_51to55.out
echo Job .err is saved at: /fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe/logs/ozstar/red_tmpl_51to55.err
echo `date`
SECONDS=0
echo -------- --------
source /fred/oz100/NOAO_archive/KNTraP_Project/src/photpipe/config/DECAMNOAO/YSE/YSE.bash.sourceme
pipeloop.pl -red tmpl 51-55 -redobad
echo -------- --------
echo `date`
duration=$SECONDS
echo Slurm Job red_tmpl_51to55 done in $(($duration / 60)) minutes and $(($duration % 60)) seconds

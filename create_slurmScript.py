#!/env/python

# Edit
slurm_job_name = 'slurm_script1'
program_path   = '/fred/oz100/NOAO_archive/KNTraP/src/KNTrap/helloworld.sh'

# Set paths
slurm_script_path = f'/fred/oz100/NOAO_archive/KNTraP/src/slurm_scripts/{slurm_job_name}.sh'
slurm_script_output_path = slurm_script_path.replace('.sh','.out')
slurm_script_errout_path = slurm_script_path.replace('.sh','.err')

# over-write mode
f = open(slurm_script_path,'w')

f.write('#!/bin/bash\n')
f.write('#\n')
f.write(f'#SBATCH --job-name={slurm_job_name}\n')
f.write(f'#SBATCH --output={slurm_script_output_path}\n')
f.write(f'#SBATCH --error={slurm_script_errout_path}\n')
f.write('#\n')
f.write('#SBATCH --nodes=1\n')
f.write('#SBATCH --ntasks-per-node=1\n')
#f.write('#SBATCH --ntasks=1\n')
f.write('#SBATCH --cpus-per-task=2\n')
f.write('#SBATCH --time=10:00')
f.write('#SBATCH --mem-per-cpu=8G\n')
f.write('#\n')
f.write('\n')
f.write(f'echo Slurm Job {slurm_job_name} START\n')
f.write('echo `date`\n')
f.write('echo -------- --------\n')
f.write(f'bash {program_path}\n')
f.write('echo -------- --------\n')
f.write('echo `date`\n')
f.write(f'echo Slurm Job {slurm_job_name} DONE\n')

f.close()

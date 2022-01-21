#!/usr/bin/env python

""" submit_slurm_OzSTAR_batch.py -- Input command to submit to sbatch, and submit it. . 

Usage: submit_slurm_OzSTAR_batch [-h] [-v] [--do_not_submit] [--ozstar_reservation STRING] [--bashrcfile STRING] <command> 

Arguments:
    command (string)
    
Options:
    -h, --help                      Show this screen
    -v, --verbose                   Print extra info to screen. [default: False]
    --do_not_submit                 Just write the slurm script and pipeline bash scripts, don't submit via sbatch [default: False]
    --bashrcfile STRING             to set up env [default: /fred/oz100/NOAO_archive/KNTraP_Project/src/photpipe/config/DECAMNOAO/YSE/YSE.bash.sourceme]
    --ozstar_reservation STRING     If set, in sbatch script put #SBATCH --reservation={ozstar_reservation}

Examples:
    submit_slurm_OzSTAR_batch.py command
"""
import docopt
import sys, os

__author__      = "Jielai Zhang"
__license__     = "MIT"
__version__     = "1.0.1"
__date__        = "2021-01-21"
__maintainer__  = "Jielai Zhang"
__email__       = "zhang.jielai@gmail.com"

def create_dir_ifnot(directory):

    if os.path.isdir(directory):
        created_or_not = False
    else:
        os.makedirs(directory)
        created_or_not = True

    return created_or_not

##############################################################
####################### Main Function ########################
##############################################################

batch_script_template = '''#!/bin/bash

#SBATCH --job-name=JOB_NAME
#SBATCH --output=/PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.out
#SBATCH --error=/PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.err

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --mem-per-cpu=12G
RESERVATION_LINE

echo Slurm Job JOB_NAME start
echo Job bash script is: JOB_BASH_SCRIPT
echo Job .out is saved at: /PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.out
echo Job .err is saved at: /PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.err
echo `date`
SECONDS=0
echo -------- --------
COMMAND
echo -------- --------
echo `date`
duration=$SECONDS
echo Slurm Job JOB_NAME done in $(($duration / 60)) minutes and $(($duration % 60)) seconds
'''

def submit_slurm_OzSTAR_batch(command,
                                bashrcfile='/fred/oz100/NOAO_archive/KNTraP_Project/src/photpipe/config/DECAMNOAO/YSE/YSE.bash.sourceme',
                                ozstar_reservation=None,
                                verbose=False,debugmode=False,quietmode=False,
                                do_not_submit=False):
    # Define slurm job name 
    slurm_job_name      = '_'.join(command.split(' '))
    fieldname           = command.split(' ')[2]

    # Figure out where to save the slurm script
    pipedata_dir = os.getenv('PIPE_DATA')
    slurm_script_dir = pipedata_dir+f'/logs/ozstar/{fieldname}'
    slurm_script_path    = slurm_script_dir+f'/{slurm_job_name}_slurm.sh'

    # Create output directory if not exist
    just_created  = create_dir_ifnot(slurm_script_dir)
    if just_created == True:
        if verbose == True or debugmode == True:
            print(f'VERBOSE/DEBUG: {slurm_script_dir} was just created.')

    # Create slurm batch bash script
    script_string = batch_script_template.replace('JOB_NAME',slurm_job_name)
    script_string = script_string.replace('PIPE_DATA_DIR',pipedata_dir)
    script_string = script_string.replace('COMMAND',command)
    script_string = script_string.replace('FIELDNAME',fieldname)
    if ozstar_reservation == None:
        script_string = script_string.replace('RESERVATION_LINE','')
    else:
        script_string = script_string.replace('RESERVATION_LINE',f'#SBATCH --reservation={ozstar_reservation}')
    
    
    # Write the bash script to file
    f = open(slurm_script_path,'w')
    f.write(script_string)
    f.close()

    # print if not quietmode
    if not quietmode:
        print(f'Saved: {slurm_script_path}')

    # submit slurm script
    if do_not_submit == False:
        command = f'sbatch {slurm_script_path}'
        print(f'Running: {command}')
        try:
            os.system(command)
        except:
            sys.exit(f'!!! ERROR-- sys.exit when running: {command}')
            
    # Finish
    return slurm_script_path


############################################################################
####################### BODY OF PROGRAM STARTS HERE ########################
############################################################################

if __name__ == "__main__":

    # Read in input arguments
    arguments           = docopt.docopt(__doc__)
    # Code running mode arguments
    debugmode           = arguments['--debug']
    if debugmode:
        print(arguments)
    verbose             = arguments['--verbose']
    quietmode           = arguments['--quietmode']
    do_not_submit       = arguments['--do_not_submit']
    # Required arguments
    command             = arguments['<command>']
    filterband          = arguments['<filterband>']
    ctio_caldate        = arguments['<ctio_caldate>']
    fitsextension       = arguments['<fitsextension>']
    # Optional arguments (with defaults set)
    bashrcfile          = arguments['--bashrcfile']
    ozstar_reservation  = arguments['--ozstar_reservation']
    # Not implemented arguments (to be implemented later)
    overwrite           = arguments['--overwrite']

    _ submit_slurm_OzSTAR_batch(command,
                                bashrcfile=bashrcfile,
                                ozstar_reservation=ozstar_reservation,
                                verbose=verbose,debugmode=debugmode,quietmode=quietmode,
                                do_not_submit=do_not_submit)

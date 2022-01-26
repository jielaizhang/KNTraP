#!/usr/bin/env python

""" submit_slurm_OzSTAR_batch.py -- Input file with commands to submit to sbatch, and submit each command. IMPORTANT: Only submit through sbatch if environment variable OZSTARSUBMIT is true. Also, only submit through sbatch if --do_not_submit is False. 
Note that   pipedata_dir      = os.getenv('PIPE_DATA')
            submit_via_sbatch = os.getenv('OZSTARSUBMIT') 

Usage: 
    submit_slurm_OzSTAR_batch [-h] [-v] [--debug] [--do_not_submit] [--ozstar_reservation STRING] [--bashrcfile STRING] [--skiplog] [--request_memory INT] <commandfile> 

Arguments:
    commandfile (string)
    
Options:
    -h, --help                      Show this screen
    -v, --verbose                   Print extra info to screen. [default: False]
    --debug                         Print input docopt arguments [default: False]
    --do_not_submit                 Just write the slurm script and pipeline bash scripts, don't submit via sbatch [default: False]
    --bashrcfile STRING             to set up env [default: /fred/oz100/NOAO_archive/KNTraP_Project/src/photpipe/config/DECAMNOAO/YSE/YSE.bash.sourceme]
    --ozstar_reservation STRING     If set, in sbatch script put #SBATCH --reservation={ozstar_reservation}
    --skiplog                       Ignore this option. 
    --request_memory INT            Request this much memory in MB [default: 8000]

Examples:
    submit_slurm_OzSTAR_batch.py command
"""
import docopt
import sys, os
import numpy as np

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
#SBATCH --mem-per-cpu=MEM_REQUESTG
RESERVATION_LINE

echo Slurm Job JOB_NAME start
echo Job bash script is: JOB_BASH_SCRIPT
echo Job .out is saved at: /PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.out
echo Job .err is saved at: /PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.err
echo `date`
SECONDS=0
echo -------- --------
source BASHRCFILE
COMMAND
echo -------- --------
echo `date`
duration=$SECONDS
echo Slurm Job JOB_NAME done in $(($duration / 60)) minutes and $(($duration % 60)) seconds
'''

def submit_slurm_OzSTAR_batch(commandfile,
                                bashrcfile='/fred/oz100/NOAO_archive/KNTraP_Project/src/photpipe/config/DECAMNOAO/YSE/YSE.bash.sourceme',
                                ozstar_reservation=None,
                                memory_request=4000,
                                verbose=False,
                                do_not_submit=False):
    # Get environment variables for pipeline set up
    pipedata_dir      = os.getenv('PIPE_DATA')
    submit_via_sbatch = os.getenv('OZSTARSUBMIT')
    if submit_via_sbatch == 'True':
        submit_via_sbatch = True
    elif submit_via_sbatch == 'False':
        submit_via_sbatch = False
    else:
        print('WARNING: OZSTARSUBMIT env variable exported to : ',submit_via_sbatch)
        print('WARNING: As a result, submit_via_sbatch set to False, prepared slurm scripts will not be sbatched.')
        submit_via_sbatch = False

    with open(commandfile) as fp:
        pipecommand = fp.readline().strip()
        cnt = 1
        while pipecommand:
            print('==========')
            print(f"Line {cnt} : {pipecommand}")

            # Define slurm job name 
            # Remove full path to "pipemaster.pl"
            pipe_command_clean  = pipecommand.split('pipemaster.pl')[1].strip()
            # Join spaces with _ and replace ' and * and / and < and > and - with nothing
            # replace __ with _
            slurm_job_name      = '_'.join(pipe_command_clean.split(' '))
            slurm_job_name      = slurm_job_name.replace("'",'')
            slurm_job_name      = slurm_job_name.replace("*",'')
            slurm_job_name      = slurm_job_name.replace("/",'')
            slurm_job_name      = slurm_job_name.replace("<",'')
            slurm_job_name      = slurm_job_name.replace(">",'')
            slurm_job_name      = slurm_job_name.replace("-",'')
            slurm_job_name      = slurm_job_name.replace("__",'_')
            # This is always the fieldname
            fieldname           = pipe_command_clean.split(' ')[1]

            # Figure out where to save the slurm script
            slurm_script_dir    = pipedata_dir+f'/logs/ozstar/{fieldname}'
            slurm_script_path   = slurm_script_dir+f'/{slurm_job_name}_slurm.sh'

            # Create output directory if not exist
            just_created  = create_dir_ifnot(slurm_script_dir)
            if just_created == True:
                if verbose == True:
                    print(f'VERBOSE/DEBUG: {slurm_script_dir} was just created.')

            # Create slurm batch bash script
            script_string = batch_script_template.replace('JOB_NAME',slurm_job_name)
            script_string = script_string.replace('PIPE_DATA_DIR',pipedata_dir)
            script_string = script_string.replace('COMMAND',pipecommand)
            script_string = script_string.replace('BASHRCFILE',bashrcfile)
            script_string = script_string.replace('FIELDNAME',fieldname)
            script_string = script_string.replace('MEM_REQUEST',str(int(np.ceil(memory_request/1000.))) )
            if ozstar_reservation == None:
                script_string = script_string.replace('RESERVATION_LINE','')
            else:
                script_string = script_string.replace('RESERVATION_LINE',f'#SBATCH --reservation={ozstar_reservation}')
            
            
            # Write the bash script to file
            f = open(slurm_script_path,'w')
            f.write(script_string)
            f.close()

            # print 
            print(f'Saved  : {slurm_script_path}')

            # submit slurm script
            if do_not_submit == False and submit_via_sbatch == True:
                sbatchcommand = f'sbatch {slurm_script_path}'
                print(f'Running: {sbatchcommand}')
                try:
                    os.system(sbatchcommand)
                except:
                    sys.exit(f'!!! ERROR-- sys.exit when running: {command}')
                print('Note   : If want to switch of submit via sbatch: put "export OZSTARSUBMIT=False"')
            else:
                print('WARNING: sbatch command not carried out as requested. To submit, put "export OZSTARSUBMIT=True"')

            # read in next line
            pipecommand = fp.readline().strip()
            cnt += 1
            
    # Finish
    return None


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
    do_not_submit       = arguments['--do_not_submit']
    # Required arguments
    commandfile         = arguments['<commandfile>']
    # Optional arguments (with defaults set)
    bashrcfile          = arguments['--bashrcfile']
    ozstar_reservation  = arguments['--ozstar_reservation']
    memory_request      = int(arguments['--request_memory'])
    _                   = arguments['--skiplog']

    _ = submit_slurm_OzSTAR_batch(commandfile,
                                bashrcfile=bashrcfile,
                                ozstar_reservation=ozstar_reservation,
                                memory_request = memory_request,
                                verbose=verbose,
                                do_not_submit=do_not_submit)

#!/usr/bin/env python

""" submit_slurm_ozstar.py -- Input fieldname, filterband, ctio_caldate, fitsextension, create a bash shell script to run the entire KNTraP pipeline, and submit it as a slurm job on OzStar. 

Usage: submit_slurm_ozstar [-h] [-q] [-v] [--debug] [--overwrite] [--do_not_submit] [--kntrap_src_path STRING] [--conda_env_name STRING] [--kntrap_data_dir STRING] [--outdir STRING] [--ozstar_reservation STRING] <fieldname> <ctio_caldate> <filterband> <fitsextension> 

Arguments:
    fieldname (string)
    ctio_caldate (string)
        e.g. 20210607
    filterband (string)
        e.g. g or r or i
    fitsextension (string)
        e.g. 30, can be 1-61

Options:
    -h, --help                          Show this screen
    -q, --quietmode                     Minimize print to screen. This is useful when this function is called in another function. [default: False]  
    -v, --verbose                       Print extra info to screen. [default: False]
    --debug                             Print debugging info to screen. [default: False]
    --overwrite                         Overwrite any existing files at destination [default: False]
    --do_not_submit                     Just write the slurm script and pipeline bash scripts, don't submit via sbatch [default: False]
    --kntrap_src_path STRING            Where src for KNTraP project lives [default: /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/]
    --conda_env_name STRING             Python conda environment name [default: kntrap]
    --kntrap_data_dir STRING            KNTraP data and working directory [default: /fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe]
    --outdir STRING                     Output the bash script here. If not set, will output in kntrap_data_dir/logs/ozstar/<fieldname>
    --ozstar_reservation STRING         If set, in sbatch script put #SBATCH --reservation={ozstar_reservation}

Examples:
    python submit_slurm_ozstar.py GRB210605A5 20210607 g 30
"""
import docopt
import subprocess, sys

# KNTraP modules
from write_kntrap_bashscript import write_kntrap_bashscript
from misc_utils import create_dir_ifnot

__author__      = "Jielai Zhang"
__license__     = "MIT"
__version__     = "1.0.1"
__date__        = "2021-01-20"
__maintainer__  = "Jielai Zhang"
__email__       = "zhang.jielai@gmail.com"

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
#SBATCH --time=10:00
#SBATCH --mem-per-cpu=8G
RESERVATION_LINE

echo Slurm Job JOB_NAME start
echo Job bash script is: JOB_BASH_SCRIPT
echo Job .out is saved at: /PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.out
echo Job .err is saved at: /PIPE_DATA_DIR/logs/ozstar/FIELDNAME/JOB_NAME.err
echo `date`
echo -------- --------
bash JOB_BASH_SCRIPT
echo -------- --------
echo `date`
echo Slurm Job JOB_NAME done
'''

def submit_slurm_ozstar(fieldname,filterband,ctio_caldate,fitsextension,
                                kntrap_src_path='/fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/',
                                conda_env_name='kntrap',
                                kntrap_data_dir='/fred/oz100/NOAO_archive/KNTraP_Project/kntrappipe',
                                outdir=None,
                                ozstar_reservation=None,
                                verbose=False,debugmode=False,quietmode=False,
                                do_not_submit=False,
                                overwrite=False):

    # Create the bash script
    kntrap_bashscript_path = write_kntrap_bashscript(fieldname,filterband,ctio_caldate,fitsextension,
                                                    kntrap_src_path=kntrap_src_path,
                                                    conda_env_name=conda_env_name,
                                                    kntrap_data_dir=kntrap_data_dir,
                                                    outdir=outdir,
                                                    verbose=verbose,debugmode=debugmode,quietmode=quietmode,
                                                    overwrite=overwrite) # overwrite function not implemented yet

    # Define slurm job name 
    slurm_job_name      = f'kntrappipe_{fieldname}_{filterband}_{ctio_caldate}_{fitsextension}'

    # Figure out where to save the bash script
    if outdir == None:
        slurm_script_dir = kntrap_data_dir+f'/logs/ozstar/{fieldname}'
    else:
        slurm_script_dir = outdir
    slurm_script_path    = slurm_script_dir+f'/kntrappipe_{fieldname}_{ctio_caldate}_{filterband}_{fitsextension}_slurm.sh'

    # Create output directory if not exist
    just_created  = create_dir_ifnot(slurm_script_dir)
    if just_created == True:
        if verbose == True:
            print(f'VERBOSE: {slurm_script_dir} was just created: {exists_already}')
        elif debugmode == True:
            print(f'DEBUG: {slurm_script_dir} was just created: {exists_already}')
    if debugmode == True and just_created == False:
        print(f'DEBUG: {slurm_script_dir} was already exists, so was not newly created.')

    # Create slurm batch bash script
    script_string = batch_script_template.replace('JOB_NAME',slurm_job_name)
    script_string = script_string.replace('PIPE_DATA_DIR',kntrap_data_dir)
    script_string = script_string.replace('JOB_BASH_SCRIPT',kntrap_bashscript_path)
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
            output = subprocess.check_output(['sbatch',slurm_script_path],shell=True)
            print(f'Ran: {command}')
            print(f'Output: {output}')
            if verbose:
                print('VERBOSE: Useful slurm queue check commands:')
                print('VERBOSE: alias watchnodes: squeue --user=fstars -i5 --format="%.11i %.9P %.29j %.8u %.7T %.8M %.4D %R"')
                print('VERBOSE: alias printnodes: squeue --user=fstars --format="%.11i %.9P %.29j %.8u %.7T %.8M %.4D %R"')
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
    fieldname           = arguments['<fieldname>']
    filterband          = arguments['<filterband>']
    ctio_caldate        = arguments['<ctio_caldate>']
    fitsextension       = arguments['<fitsextension>']
    # Optional arguments (with defaults set)
    kntrap_src_path     = arguments['--kntrap_src_path']
    conda_env_name      = arguments['--conda_env_name']
    kntrap_data_dir     = arguments['--kntrap_data_dir']
    outdir              = arguments['--outdir']
    ozstar_reservation  = arguments['--ozstar_reservation']
    # Not implemented arguments (to be implemented later)
    overwrite           = arguments['--overwrite']

    _ = submit_slurm_ozstar(fieldname,filterband,ctio_caldate,fitsextension,
                                kntrap_src_path=kntrap_src_path,
                                conda_env_name=conda_env_name,
                                kntrap_data_dir=kntrap_data_dir,
                                outdir=outdir,
                                ozstar_reservation=ozstar_reservation,
                                verbose=verbose,debugmode=debugmode,quietmode=quietmode,
                                do_not_submit =  do_not_submit,
                                overwrite=overwrite)
                                # overwrite function not yet fully implemented. 

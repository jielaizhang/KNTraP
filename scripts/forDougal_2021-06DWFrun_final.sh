# No Spread Model Version

cd /fred/oz100/NOAO_archive/CPtrigger_data/data/2021
source activate py3.6
export PYTHONPATH=$PYTHONPATH:/fred/oz100/jielaizhang/src/dataexplore/
module load psfex/3.21.1

#STEP1: split CPTrigger stack fits file's 9 exts into 9 fits files
python /fred/oz100/jielaizhang/src/dataexplore/datavis/fits/extract_extensions.py -v 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack.fits 1,2,3,4,5,6,7,8,9 
python /fred/oz100/jielaizhang/src/dataexplore/datavis/fits/extract_extensions.py -v 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_sd.fits 1,2,3,4,5,6,7,8,9 

# ===========================================================================
# For each DECam pointing, every step below this note
# needs to be done 9 times:
# for 9 science images, one for each of the 1-9 extensions created in #STEP1.
# ===========================================================================

#STEP2: align template and science image, output template_resamp.fits and science_resamp.fits
# overall syntax: align_image --swarp swarp_loc -o save_in_this_dir template.fits science.fits
python /fred/oz100/jielaizhang/src/dataexplore/datavis/fits/align_image.py --swarp /apps/skylake/software/compiler/gcc/6.4.0/swarp/2.38.0/bin/swarp -o 20210605/GRB210605Agreen1/g/ /fred/oz100/pipes/DWF_PIPE/TEMPLATES/GRB210605Agreen1/GRB210605Agreen1_g_stacked_temp.fits 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.fits

# STEP3: subtract template and science image, output subtraction.fits
# overall syntax: subtract_image --sextractor SE_loc template_resamp.fits and science_resamp.fits -s subtraction.fits d
python /fred/oz100/jielaizhang/src/dataexplore/datavis/fits/subtract_image.py --sextractor /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex 20210605/GRB210605Agreen1/g/GRB210605Agreen1_g_stacked_temp.resamp.fits 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp.fits -s 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub.fits

# STEP4: source extract template image, output template.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR template.fits
python /fred/oz100/jielaizhang/src/dataexplore/datastats/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending TEMPL --fwhm 1.1 --detect_minarea 10 --detect_thresh 1.0 --savecats 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_g_stacked_temp.resamp.fits

# PRE-STEP5: turn CCD gaps etc into nans in science image
python /fred/oz100/jielaizhang/src/dataexplore/misc/nanify_with_mask_DECam.py 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp.fits 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_sd_ext5.resamp.fits -o 20210605/GRB210605Agreen1/g/

# STEP5: source extract science image, output science.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR science.fits
python /fred/oz100/jielaizhang/src/dataexplore/datastats/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending SCI --fwhm 1.1 --detect_minarea 10 --detect_thresh 1.0 --savecats 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_withnans.fits

# PRE-STEP6: turn CCD gaps etc into nans in science image
python /fred/oz100/jielaizhang/src/dataexplore/misc/nanify_with_mask_DECam.py 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub.fits 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_sd_ext5.resamp.fits -o 20210605/GRB210605Agreen1/g/


# STEP6: source extract subtraction image, output subtraction.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR subtraction.fits
# !!!! This step takes in the output from pre-step6 instead of what it used to take in.
python /fred/oz100/jielaizhang/src/dataexplore/datastats/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending SUB --fwhm 1.1 --detect_minarea 10 --detect_thresh 1.0 --savecats 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans.fits 

# STEP7: invert the subtraction image , output inv_subtraction.fits
# overall syntax: invert -o OUTPUT_DIR --options subtraction.fits
python /fred/oz100/jielaizhang/src/dataexplore/datavis/fits/invert_fits.py -o 20210605/GRB210605Agreen1/g/ --overwrite 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans.fits

# STEP8: source extract inverted subtraction image, output inv_subtraction.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR subtraction.fits 
python /fred/oz100/jielaizhang/src/dataexplore/datastats/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending NEG --fwhm 1.1 --detect_minarea 8 --detect_thresh 1.0 --savecats 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans_neg.fits

# STEP9: read subtraction.cat, inverted sub, sci, templ catalogues and deteremine best new transient candidates; outputs 3 ds9 region files
# overall syntax: find_new_transients -o OUTPUT_DIR sub.cat sci.cat inverted_sub.cat template.cat
python /fred/oz100/jielaizhang/src/dataexplore/datavis/ascii/find_new_transientCandidates_DECam.py -v -o 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans_SUB.cat 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_withnans_SCI.cat 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans_neg_NEG.cat 20210605/GRB210605Agreen1/g/GRB210605Agreen1_g_stacked_temp.resamp_TEMPL.cat


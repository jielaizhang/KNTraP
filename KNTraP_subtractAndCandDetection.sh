# No Spread Model Version

cd /fred/oz100/NOAO_archive/KNTraP_Project/
source activate py3.6
export PYTHONPATH=$PYTHONPATH:/fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/
module load psfex/3.21.1

#STEP1: split CPTrigger stack fits file's 61 exts into 61 fits files
# This was done manually as it involved for NOAO archive data getting instcal, then splitting into CCDs then stacking after splitting it. 
# This would not be the observing run procedure.

# ===========================================================================
# For each DECam pointing, every step below this note
# needs to be done for each CCD split out in #STEP1.
# ===========================================================================

#STEP2: align template and science image, output template_resamp.fits and science_resamp.fits
# overall syntax: align_image --swarp swarp_loc -o save_in_this_dir template.fits science.fits
python /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/align_image.py --swarp /apps/skylake/software/compiler/gcc/6.4.0/swarp/2.38.0/bin/swarp -o data_outputs/GRB210605A5/20210607 TEMPLATE_IMAGES/GRB210605A5_g_stacked_template.fits data_unpacked/GRB210605A5/GRB210605A5_20210607/GRB210605A5_20210607_g_stack_ext30.fits
mv data_outputs/GRB210605A5/20210607/GRB210605A5_g_stacked_template.resamp.fits data_outputs/GRB210605A5/20210607/GRB210605A5_g_stacked_template_ext30.resamp.fits

# STEP3: subtract template and science image, output subtraction.fits
# overall syntax: subtract_image --sextractor SE_loc template_resamp.fits and science_resamp.fits -s subtraction.fits d
python /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/subtract_image.py --sextractor /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex data_outputs/GRB210605A5/20210607/GRB210605A5_g_stacked_template_ext30.resamp.fits data_outputs/GRB210605A5/20210607/GRB210605A5_20210607_g_stack_ext30.resamp.fits -s data_outputs/GRB210605A5/20210607/GRB210605A5_20210607_g_stack_ext30.resamp_sub.fits

# STEP4: source extract template image, output template.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR template.fits
python /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending TEMPLATE --fwhm 1.1 --detect_minarea 10 --detect_thresh 1.0 --savecats data_outputs/GRB210605A5/20210607 data_outputs/GRB210605A5/20210607/GRB210605A5_g_stacked_template_ext30.resamp.fits


# above edited a bit

# STEP5: source extract science image, output science.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR science.fits
python /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending SCI --fwhm 1.1 --detect_minarea 10 --detect_thresh 1.0 --savecats 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_withnans.fits

# STEP6: source extract subtraction image, output subtraction.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR subtraction.fits
# !!!! This step takes in the output from pre-step6 instead of what it used to take in.
python /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending SUB --fwhm 1.1 --detect_minarea 10 --detect_thresh 1.0 --savecats 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans.fits 

# STEP7: invert the subtraction image , output inv_subtraction.fits
# overall syntax: invert -o OUTPUT_DIR --options subtraction.fits
python /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/invert_fits.py -o 20210605/GRB210605Agreen1/g/ --overwrite 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans.fits

# STEP8: source extract inverted subtraction image, output inv_subtraction.cat
# overall syntax: run_sourceextractor -s SE_loc -p PSFEX_loc --options --savecats OUTPUT_DIR subtraction.fits 
python /fred/oz100/NOAO_archive/KNTraP_Project/src/KNTraP/run_sourceextractor.py -v -s /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/sextractor/2.19.5/bin/sex -p /apps/skylake/software/mpi/gcc/6.4.0/openmpi/3.0.0/psfex/3.21.1/bin/psfex --catending NEG --fwhm 1.1 --detect_minarea 8 --detect_thresh 1.0 --savecats 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans_neg.fits

# STEP9: read subtraction.cat, inverted sub, sci, templ catalogues and deteremine best new transient candidates; outputs 3 ds9 region files
# overall syntax: find_new_transients -o OUTPUT_DIR sub.cat sci.cat inverted_sub.cat template.cat
python /fred/oz100/jielaizhang/src/dataexplore/datavis/ascii/find_new_transientCandidates_DECam.py -v -o 20210605/GRB210605Agreen1/g/ 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans_SUB.cat 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_withnans_SCI.cat 20210605/GRB210605Agreen1/g/GRB210605Agreen1_20210605_g_stack_ext5.resamp_sub_withnans_neg_NEG.cat 20210605/GRB210605Agreen1/g/GRB210605Agreen1_g_stacked_temp.resamp_TEMPL.cat


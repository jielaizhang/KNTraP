# Author: Igor Andreoni
import glob
import subprocess

if __name__ == "__main__":
    # Copy the catalogs for photometric calibration in the right directories
    import argparse
    parser = argparse.ArgumentParser(description='Copy the photometric catalogs\
in photpipe directories')

    parser.add_argument('-c', '--catalog',
                        dest='catname', type=str,
                        default='*',
                        help='Catalog to be copied (SM, PS1, APASS, *)')
    parser.add_argument('-i', '--start-path',
                        dest='path_start', type=str,
                        default='catalogs_photometry',
                        help='Path to the directory where the files are \
saved')
    args = parser.parse_args()


    # Path to the directory where the files will be saved
    inpathdir = args.path_start
    outpathdir_base = '/fred/oz100/NOAO_archive/KNTraP_Project/photpipe/v20.0/\
DECAMNOAO/KNTraP/abscats/'

    # For each filter
    for filt in ["g", "i"]:
        if filt == 'g':
            outputpathdir = outpathdir_base + "0x5013/"
            files = glob.glob(f"{inpathdir}/*_g_*{args.catname}*cat")
        elif filt == 'i':
            outputpathdir = outpathdir_base + "0x5015/"
            files = glob.glob(f"{inpathdir}/*_i_*{args.catname}*cat")
        for f in files:
            cmd_list = ["cp", f,  outputpathdir + f.split("/")[-1]]
            subprocess.call(cmd_list)

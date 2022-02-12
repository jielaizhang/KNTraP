import glob
import subprocess

if __name__ == "__main__":
    # Copy the catalogs for photometric calibration in the right directories

    catname = 'APASS'
    # Path to the directory where the files will be saved
    inpathdir = 'catalogs_photometry/'
    outpathdir_base = '/fred/oz100/NOAO_archive/KNTraP_Project/photpipe/v20.0/\
DECAMNOAO/KNTraP/abscats/'

    # For each filter
    for filt in ["g", "i"]:
        if filt == 'g':
            outputpathdir = outpathdir_base + "0x5013/"
            files = glob.glob(f"{inpathdir}/*_g_*cat")
        elif filt == 'i':
            outputpathdir = outpathdir_base + "0x5015/"
            files = glob.glob(f"{inpathdir}/*_i_*cat")
        for f in files:
            cmd_list = ["cp", f,  outputpathdir + f.split("/")[-1]]
            subprocess.call(cmd_list)

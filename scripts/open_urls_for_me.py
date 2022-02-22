from astropy.io import ascii
import numpy as np
import webbrowser
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help = "Input selected CSV file")
args = parser.parse_args()
filename = args.file

if filename == None:
    print('To get the required files for this program, do this: ')
    string = 'rsync -avzP fstars@ozstar.swin.edu.au:/fred/oz100/NOAO_archive/KNTraP_Project/photpipe/v20.0/DECAMNOAO/KNTraP/KNTrap_selection/Fink_outputs/caldatYYYYMMDD/* .'
    print(string)
    sys.exit("EXIT: please input a selected_FIELD_tmpl.csv file")

number_urls_to_open_at_once = 10

d        = ascii.read(filename,delimiter=';')
baseurl      = 'http://kntrap-bucket.s3-website-us-east-1.amazonaws.com'
ccds         = []
inspect_ids  = d['id']
number_open  = 0
total_opened = 0
input_key    = 'BLAH'
for_loop_break = False
for ID in inspect_ids:
    field = ID.split('_')[0]
    ccd   = ID.split('_')[1].split('.')[0]
    run   = ID.split('_')[1].split('.')[1]
    cand  = ID.split('_')[-1].replace('cand','')
    url = f'{baseurl}/sniff-deep/{field}_tmpl/{ccd}/{field}_{ccd}.{run}/index.html#{cand}'
    ccds.append(ccd)
    webbrowser.open(url)
    number_open += 1
    total_opened +=1
    if number_open == number_urls_to_open_at_once:
        while input_key == 'BLAH':
            input_key = input(f"Opened {total_opened}/{len(inspect_ids)} tabs so far.Press c: continue; Press q: quit.")
            if input_key == 'q':
                print('Input: ',input_key)
                for_loop_break = True
                break
            if input_key == 'c':
                print('Input: ',input_key)
                pass
            else:
                print('Input: ',input_key)
        input_key = 'BLAH'
        number_open = 0
        if for_loop_break == True:
            break
            
print(f'You have looked at at least one source on the following {len(np.unique(ccds))} CCDs \n',np.unique(ccds))



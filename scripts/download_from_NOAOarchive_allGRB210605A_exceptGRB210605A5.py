#!/usr/bin/env python

############################# HOW TO RUN IN TERMINAL
# python download_from_NOAOarchive.py 2>&1 | tee download_from_NOAOarchive.out
# Can run from directory containing this script, and .out will be saved and can be gitted.

############################# 
# Clear after use
usrname = 'XXX'
pw      = 'XXX'

############################# 
save_dir = '/fred/oz100/NOAO_archive/KNTraP_Project/data_unpacked/' 
 
############################# IMPORTS

import sys, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import astropy.io.fits as pyfits
import astropy.utils as autils
import requests
import json
import datetime
from pprint import pprint as pp
import subprocess
import time

############################# SETUP

# Time Counter function
def tic():
    tic.start = time.perf_counter()
def toc():
    elapsed_seconds = time.perf_counter() - tic.start
    return elapsed_seconds # fractional

# NOAO server Settings
natroot = 'https://astroarchive.noirlab.edu'
assert natroot == 'https://astroarchive.noirlab.edu', 'Notebook does NOT point to PRODUCTION'
print(f"Using server on {natroot}")
adsurl = f'{natroot}/api/adv_search'
print(f"adsurl = {adsurl}")

# Start the timer
print(f'Started on: {str(datetime.datetime.now())}')
tic() # Start timing the run of this notebook

############################# QUERY

jj = {
    "outfields" : [
        "md5sum",
        "archive_filename",
        #"telescope",
        #"instrument",
        #"obs_type",
        #"proc_type",
        #"prod_type",
        #"proposal",
        "ra_center",
        "dec_center",
        "caldat",
        "url",
        "filesize",
        "ifilter",
        "exposure",
        "dateobs_min",
        "dateobs_max",
    ],
    "search" : [
        ["obs_type", 'object'],
        ["proposal","2020B-0253"],
        ["proc_type","instcal"],
        ["prod_type", "image"],
        ["caldat","2020-06-01", "2021-06-11"]
    ]
}
apiurl = f'{adsurl}/fasearch/?limit=200000'
print(f'Using API url: {apiurl}')
ads_df = pd.DataFrame(requests.post(apiurl,json=jj).json()[1:])
ads_df

############################# DOWNLOAD 
dic_fieldname_coordinates = {
    'GRB210605Agreen1' : [21.1779500,-39.9611111,0.03],
    'GRB210605Agreen2' : [18.9162908,-42.1027781,0.03],
    'GRB210605Agreen3' : [23.2478742,-40.6750000,0.03],
    'GRB210605Agreen4' : [19.3151779,-39.9611111,0.03],
    'GRB210605Agreen5' : [20.8406671,-42.1027781,0.03],
    'GRB210605Apink1' : [17.7672100,-41.3888890,0.03],
    'GRB210605Apink2' : [21.8494173,-42.0508599,0.03],
    'GRB210605Apink3' : [17.3120418,-39.2597284,0.03],
    'GRB210605Apink4' : [22.6885000,-38.5333330,0.03],
    'GRB210605Apink5' : [19.9506640,-38.5333330,0.03],
    'GRB210605A5' : [24.2083333, -48.7500000,1.0],
    'GRB210605A4' : [23.0416667, -47.0944444,0.05],
    'GRB210605A3' : [21.9583333, -45.4583333,0.6],
    'GRB210605A2' : [20.9375000, -43.8000000,0.05],
    'GRB210605A1' : [19.9791667, -42.1750000,0.2]
}

for field_name,c in dic_fieldname_coordinates.items():
    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    print('Downloading data for new field: ',field_name,c)
    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    if os.path.isdir(save_dir+os.sep+field_name):
        print(f'{save_dir+os.sep+field_name} exists.')
    else:
        os.makedirs(save_dir+os.sep+field_name)
        print(f'{save_dir+os.sep+field_name} -- directory made')
    field_RA             = dic_fieldname_coordinates[field_name][0]
    field_DEC            = dic_fieldname_coordinates[field_name][1]
    dec_offset_allowance = dic_fieldname_coordinates[field_name][2] # 0.05
    RA_offset_allowance  = np.abs(dec_offset_allowance*np.cos(field_DEC))
    print('(dec_offset_allowance,RA_offset_allowance,np.cos(field_DEC): ',
          dec_offset_allowance,RA_offset_allowance,np.cos(field_DEC)
         )
    ra_min = field_RA-RA_offset_allowance
    ra_max = field_RA+RA_offset_allowance
    dec_min = field_DEC-dec_offset_allowance
    dec_max = field_DEC+dec_offset_allowance
    field_ads_df = ads_df[( (ads_df['ra_center']>ra_min) & (ads_df['ra_center']<ra_max) &
                            (ads_df['dec_center']<dec_max) & (ads_df['dec_center']>dec_min)
                         )]
    print(len(field_ads_df))

    for index, row in field_ads_df.iterrows():
        print('=================================')
        print('WORKING ON DOWNLOADING A NEW FILE')
        print(row)
        dlink  = row['url']
        caldat = row['caldat'].replace('-','')
        band   = row['ifilter'].split(' ')[0]
        ra     = float(row['ra_center'])
        dec    = float(row['dec_center'])
        obs_min= row['dateobs_min'].split('.')[0].replace('-','').replace(':','')
        fname  = f'CPinstcal_{field_name}_{caldat}_{obs_min}_ooi_{band}_{ra:.3f}_{dec:.3f}.fits.fz'
        fileID = row['md5sum']
        print(' ')
        print('archive_filename: ',row['archive_filename'])
        print(' ')
        print('Will save as: ',fname)

        headers = dict()
        fileurl = f'{natroot}/api/retrieve/{fileID}'
        tokurl = f'{natroot}/api/get_token/'
        auth = dict(email=usrname, password=pw)
        print(f'tokurl={tokurl}\n\nfileurl={fileurl}')

        print('\n,,,,,,,,,,\n')

        print(f'For {fname}:')
        r = requests.post(tokurl, json=auth)
        if r.status_code == 200:
            token = r.json()
            headers = dict(Authorization=token)
            print(f'headers={headers}\n')
            r2 = requests.get(fileurl,headers=headers)
            if r2.status_code == 200:
                print(f'\nRead file with size={len(r2.content):,} bytes')
                open(save_dir+os.sep+field_name+os.sep+fname, 'wb').write(r2.content) # write temp file
                print(f'Saved: {save_dir}/{field_name}/{fname}')
            else:
                msg = f'Error getting file ({requests.status_codes._codes[r2.status_code][0]}). {r2.json()["message"]}'
                raise Exception(msg)
        else:
            token = None
            raise Exception(f"Could got get authorization: {token['detail']}")



############################# WRAP UP
print('\n#############################')
print('#############################')
print('#############################')
elapsed = toc()
print(f'Elapsed seconds={elapsed} on {natroot}')
print(f'Completed on: {str(datetime.datetime.now())}')

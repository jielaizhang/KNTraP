#!/usr/bin/env python

############################# HOW TO RUN IN TERMINAL
# python download_from_NOAOarchive.py 2>&1 | tee download_from_NOAOarchive.out

############################# 
# Clear after use
pw = 'XXXX'
usrname = 'XXX'

############################# 
save_dir = '/fred/oz100/NOAO_archive/KNTraP_Project/data_unpacked/GRB210605A5/'
 
############################# IMPORTS

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import astropy.io.fits as pyfits
import astropy.utils as autils
import requests
import json
import datetime
from pprint import pprint as pp

# Jielai added modules 
import subprocess

############################# SETUP

# Time Counter function
import time
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
        "proc_type",
        "prod_type",
        #"release_date",
        "proposal",
        "ra_center",
        #"ra_min",
        "dec_center",
        #"dec_min",
        "caldat",
        "url",
        "filesize",
        "ifilter",
        #"seeing",
        "exposure",
        #"depth",
        "dateobs_min",
        "dateobs_max",
    ],
    "search" : [
        #["release_date", "2020-01-01", "2021-01-01"], # proprietary
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

############################# FILTER and DOWNLOAD 1

field_name = 'GRB210605A5a'
field_RA   =  24.208333
field_DEC  = -48.7500000
def_offset_allowance = 0.3
RA_offset_allowance  = def_offset_allowance*np.cos(field_DEC)
ra_min  = field_RA-RA_offset_allowance
ra_max  = field_RA+RA_offset_allowance
dec_min = field_DEC-def_offset_allowance
dec_max = field_DEC+def_offset_allowance
print(ra_min,ra_max,dec_min,dec_max)
ads_df_select = ads_df[( (ads_df['ra_center']>ra_min) & (ads_df['ra_center']<ra_max) &
                         (ads_df['dec_center']<dec_max) & (ads_df['dec_center']>dec_min)
                      )]
print(len(ads_df_select))
ads_df_select

for index, row in ads_df_select.iterrows():
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
            open(save_dir+fname, 'wb').write(r2.content) # write temp file
            print(f'Saved: {save_dir}{fname}')
        else:
            msg = f'Error getting file ({requests.status_codes._codes[r2.status_code][0]}). {r2.json()["message"]}'
            raise Exception(msg)
    else:
        raise Exception(f"Could got get authorization: {token['detail']}")


############################# FILTER and DOWNLOAD 2

field_name = 'GRB210605A5b'
field_RA   =  24.164
field_DEC  = -48.717
def_offset_allowance = 0.5
RA_offset_allowance  = def_offset_allowance*np.cos(field_DEC)
ra_min  = field_RA-RA_offset_allowance
ra_max  = field_RA+RA_offset_allowance
dec_min = field_DEC-def_offset_allowance
dec_max = field_DEC+def_offset_allowance
print(ra_min,ra_max,dec_min,dec_max)
ads_df_select = ads_df[( (ads_df['ra_center']>ra_min) & (ads_df['ra_center']<ra_max) &
                         (ads_df['dec_center']<dec_max) & (ads_df['dec_center']>dec_min)
                      )]
print(len(ads_df_select))
ads_df_select

for index, row in ads_df_select.iterrows():
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
            open(save_dir+fname, 'wb').write(r2.content) # write temp file
            print(f'Saved: {save_dir}{fname}')
        else:
            msg = f'Error getting file ({requests.status_codes._codes[r2.status_code][0]}). {r2.json()["message"]}'
            raise Exception(msg)
    else:
        raise Exception(f"Could got get authorization: {token['detail']}")


############################# WRAP UP
print('\n#############################')
print('#############################')
print('#############################')
elapsed = toc()
print(f'Elapsed seconds={elapsed} on {natroot}')
print(f'Completed on: {str(datetime.datetime.now())}')

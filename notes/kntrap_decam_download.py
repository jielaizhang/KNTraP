#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun  7 19:27:04 2021

@author: arest, based on code from ckilpatrick
"""

import sys,requests,shutil,os,copy,re,glob
import pandas as pd
import numpy as np
from astropy.utils.data import download_file
from astropy.table import Table, vstack
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time
#import urllib.error
import warnings
import argparse
import filecmp
import astropy.io.fits as fits
from pandas.core.dtypes.common import is_object_dtype,is_float_dtype,is_integer_dtype
from astropy import units as u


if 'PIPE_PYTHONSCRIPTS' in os.environ:
    sys.path.append(os.environ['PIPE_PYTHONSCRIPTS'])
    sys.path.append(os.environ['PIPE_PYTHONSCRIPTS']+'/tools')
from pdastro import pdastroclass, AnotB, AandB, unique, rmfiles

warnings.filterwarnings('ignore')

# https://astroarchive.noirlab.edu/api/fields/


#natroot='https://astroarchive.noirlab.edu'
#adsurl = f'{natroot}/api/adv_search'

def parse_coord(ra, dec):
    coord = None
    if ':' in str(ra) and ':' in str(dec):
        coord = SkyCoord(ra, dec, unit=(u.hour, u.deg), frame='icrs')
    else:
        coord = SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs')
    return(coord)

def makepath(path,raiseError=1):
    if path == '':
        return(0)
    if not os.path.isdir(path):
        os.makedirs(path)
        if not os.path.isdir(path):
            if raiseError == 1:
                raise RuntimeError('ERROR: Cannot create directory %s' % path)
            else:
                return(1)
    return(0)

def makepath4file(filename,raiseError=1):
    path = os.path.dirname(filename)
    if not os.path.isdir(path):
        return(makepath(path,raiseError=raiseError))
    else:
        return(0)

def getlimits(lims):
    if lims is None or len(lims)==0:
        return(None)
    if len(lims)==1:
        if re.search('\+$',lims[0]):
            lims[0]=re.sub('\+$','',lims[0])
            return([lims[0],None])
        elif  re.search('\-$',lims[0]):
            lims[0]=re.sub('\-$','',lims[0])
            return([None,lims[0]])
        else:
            return([lims[0],lims[0]])    
    elif len(lims)==2:
        return([lims[0],lims[1]])    
    else:
        raise RuntimeError(f'limits can have only 2 entries, more given! {lims}')
 
def rmfile(filename,raiseError=True):
    " if file exists, remove it "
    if os.path.lexists(filename):
        os.remove(filename)
        if os.path.isfile(filename):
            if raiseError == 1:
                raise RuntimeError('ERROR: Cannot remove %s' % filename)
            else:
                return(1)
    return(0)


class kntrap_decam_downloadclass(pdastroclass):
    def __init__(self,url='https://astroarchive.noirlab.edu'):
        pdastroclass.__init__(self)
        
        self.verbose=0
        self.debug=0
        
        self.rooturl=url.rstrip("/")
        self.apiurl = f'{self.rooturl}/api'
        self.adsurl = f'{self.rooturl}/api/adv_search'
        self.apiretrieve = f'{self.apiurl}/retrieve'
        self.apiheader = f'{self.apiurl}/header'

        self.pointingtable = pdastroclass()
        self.racol = None
        self.deccol= None

        # IDcol is the column that connects the pointingtable with the product
        # table: The IDcol values get copied to the image table column 
        # with the same name. This will be used to associate the 2 tables.
        self.IDcol = None

        self.filters={'u':'u DECam c0006 3500.0 1000.0',
                      'g':'g DECam SDSS c0001 4720.0 1520.0',
                      'r':'r DECam SDSS c0002 6415.0 1480.0',
                      'i':'i DECam SDSS c0003 7835.0 1470.0',
                      'z':'z DECam SDSS c0004 9260.0 1520.0',
                      'y':'Y DECam c0005 10095.0 1130.0',
                      'VR':'VR DECam c0007 6300.0 2600.0'}

        self.corecolumns = {
                "EXPNUM":pd.Int64Dtype(),
                "OBJECT":str,
                "EXPTIME":float,
                "ra_center": float,
                "dec_center": float,
                "proposal": str,
                "dateobs_center": str,
                "proc_type": str,
                "prod_type": str,
                "obs_type": str,
                "md5sum": str,
                "archive_filename": str,
                "release_date": str,
#                "caldat":str,
#                "seeing": float,
#                "depth": float,
#                "ra_min": float,
#                "ra_max": float,
#                "dec_min": float,
#                "dec_max": float,
                "instrument": str,
                "telescope": str,
#                "url": str,
                "ifilter": str,
            }
          
        # DECam FOV diameter
        self.FOV_diameter_deg=2.2
        # DECam pixel scale in center is 0.2637 arcsec/pixel, and on the edge is 0.2626 arcsec/pixel 
        self.pixelscale = 0.2637 
        # calculate the box size of the detectors in degrees
        self.detector_boxsize_Dec = self.pixelscale*2048.0/3600.0
        self.detector_boxsize_RA = self.pixelscale*4096.0/3600.0
        
        # This is for matching detectors to tiles: set  self.tile_boxsize_Dec 
        # and self.tile_boxsize_RA according to thetilepattern used.
        # MAKE SURE self.tilepatternmode IS THE SAME THAT WAS USED TO CREATE
        # THE FIELDCENTERS FILE!
        #self.tilepatternmode='detector'
        # if self.tile_boxsize_Dec = self.tile_boxsize_RA = None, then 
        # they are determined automatically from the self.tilepatternmode.
        # if they are unequal to None, they override the boxsizes determined from
        # self.tilepatternmode, so be careful when you set these! 
        #self.tile_boxsize_Dec = self.tile_boxsize_RA = Nonezero
        # You can add extra padding to EACH side of the tiles
        #self.tile_boxsize_padding_arcsec = None

        # placeholder for tile boxsize. Needs to be set for photpipe_outfilename!
        self.tile_boxsize_Dec = self.tile_boxsize_RA = None
        # the overlap fraction is calculated as the overlap area between 
        # detector and tile, divided by the area of the detector. This means that
        # the overlap_fraction = 1.0 if the detector is fully within the tile.
        # a detecor images is included into a tile of the 
        # overlap_fraction >= self.min_overlap_fraction
        self.min_overlap_fraction=0.1
        
        # extra columns to retrieve from the archive: Make sure they are valid!!
        # https://astroarchive.noirlab.edu/api/fields/
        self.aux_columns_archive=[]
        
        # list of columns that should be copied from the pointing table to the image table
        self.pointing2im_columns=[]

        self.imoutcols = []
        # self.imoutcols_short is used if  --imoutcols short
        self.imoutcols_short = ['proc_type','prod_type','archive_filename','dateobs_center']

        # This flag is set if Image quality information was obtained
        self.image_quality = False # Grab image quality info for each image?
        # What hdu values do we need to query for each image to construct image
        # quality information?
        self.image_quality_columns = {
            "EXPNUM":pd.Int64Dtype(),
            "OBJECT":str,
            "EXPTIME":float,
            "hdu:ra_center": float,
            "hdu:dec_center": float,
            "proposal": str,
            "dateobs_center": str,
            "proc_type": str,
            "prod_type": str,
            "obs_type": str,
            "md5sum": str,
            "archive_filename": str,
            "release_date": str,
            "instrument": str,
            "telescope": str,
            "ifilter": str,
            "hdu:FWHM": float,
            "hdu:AVSIG": float,
            "MAGZPT": float,
            "MAGZERO": float,
            "hdu:CCDNUM": int,
        }
        
        self.token=None
        if 'NOIR_API_TOKEN' in os.environ:
            self.token=os.environ['NOIR_API_TOKEN']
        
        return(0)
    
    def NOIRlogin(self,email,password):
        res = requests.post(f'{self.apiurl}/get_token/',
                            json=dict(email=email, password=password))
        res.raise_for_status()
        if res.status_code == 200:
            self.token = res.json()
            if self.verbose>1: print('NOIR API token:', self.token)
        else:
            self.token = None
            msg = (f'Credentials given '
                   f'(email="{email}", password={password}) '
                   f'could not be authenticated. Therefore, you will '
                   f'only be allowed to retrieve PUBLIC files. '
                   f'You can still get any metadata.' )
            raise Exception(msg) 
            
    def setIDcol(self,IDcol=None):
        # make sure self.IDcol is set to something!
        if IDcol is None:
            if self.IDcol is None:
                self.IDcol = 'Posname'
        else:
            self.IDcol = IDcol

        # make sure the self.IDcol is copied from the pointing table to the image table
        if not (self.IDcol in self.pointing2im_columns):
            self.pointing2im_columns.append(self.IDcol)
        return(0)
        

    def add_arguments(self, parser=None, usage=None, conflict_handler='resolve'):
        if parser is None:
            parser = argparse.ArgumentParser(usage=usage, conflict_handler=conflict_handler)
            
        default_outrootdir = '.'
        if 'PIPE_DATA' in os.environ:
            default_outrootdir = f"{os.environ['PIPE_DATA']}/rawdata"
        
        default_pointingfile=default_fieldcentersfile=None
        if 'PIPE_CONFIGDIR' in os.environ:
            default_pointingfile=f'{os.environ["PIPE_CONFIGDIR"]}/{os.environ["PIPENAME"]}.pointings.txt'
            default_fieldcentersfile=f'{os.environ["PIPE_CONFIGDIR"]}/{os.environ["PIPENAME"]}.fieldcenters'    
                    
        parser.add_argument('-v', '--verbose', action='count', default=0)
        parser.add_argument('--debug', action='count', default=0)

        #group_radius = parser.add_argument_group("Options that define the search radius")
        #parser.add_argument('--any_overlap', action='store_true', default=False, help='find images that have potentially any overlap with a DECam image taken at the given position. Since the radius of the DECam FOV is 1.1 degree, this means that the search radius is 2.2 deg')
        parser.add_argument('-r','--searchradius', nargs="+", default=["1.1","deg"], help='Find images which center is within this search radius. Note that a radius of 2.2 deg finds images that have potentially any overlap with a DECam image taken at the given position (since FOV radius is 1.1 deg)')

        parser.add_argument('-s', '--skip_confirm_download', action='store_true', default=False,help='Download of the data without confirming it')
        parser.add_argument('--clobber', action='store_true', default=False,help='clobber the output files')
        parser.add_argument('--skip_check_if_outfile_exists', action='store_true', default=False,help='Don\'t check if output files exists. This makes it faster for large lists')        

        parser.add_argument('--login', default=None, nargs=2, help='username and password for login')
        parser.add_argument('--token', default=None, help='token for login')

        parser.add_argument('--aux_columns', nargs="+", default=[], help='specify list of auxiliary entries to retrieve from the archive. This can be used to obtain fits keywords, but you have to make sure that the entries exists, see https://astroarchive.noirlab.edu/api/fields/ (default=%(default)s)')
        parser.add_argument('--pointing2im_columns', nargs="+", default=[], help='specify list of columns to be copied from the pointing table to the image table (default=%(default)s)')

        parser.add_argument('-f','--fieldcenter_file', default=default_fieldcentersfile, help='fieldcenters filename (default=%(default)s)')
        parser.add_argument('--pointingfile', default=default_pointingfile, help='filename of list of pointing positions for download (default=%(default)s)')


        parser.add_argument('--racol', default='RA', help='RA column name in pointing file (default=%(default)s)')
        parser.add_argument('--deccol', default='Dec', help='Dec column name in pointing file (default=%(default)s)')
        parser.add_argument('--IDcol', default='field', help='Column name for the IDs. These IDs are used to associate the positions with the image table (default=%(default)s)')
#        parser.add_argument('--outfieldcol', default=None, help='output field column name of input list (default=%(default)s)')
        parser.add_argument('--ID_select', nargs="+", default=None, help='Select the ID or ID range to download. This will be applied to the --IDcol column of the pointing table. If single value, then exact match. If single value has "+" or "-" at the end, then it is a lower and upper limit, respectively. Examples: 296A, 296A+, 296A-, 296A-440F (default=%(default)s)')
        parser.add_argument('--IDs', nargs='+', default=None, help='Specify IDs to download. This will be applied to the --IDcol column of the pointing table.')


        parser.add_argument('--proc_type', nargs="+", choices=['instcal','raw','resampled','skysub','stacked','mastercal','projected'], default=['instcal'], help='specify processing types (default=%(default)s)')
        parser.add_argument('--prod_type', nargs="+", choices=['image','dqmask','wtmap','expmap','image1'], default=['image','dqmask','wtmap'], help='specify product types (default=%(default)s)')
        parser.add_argument('--obs_type', nargs="+", choices=['object','zero'], default=['object'], help='specify observation types (default=%(default)s)')
        parser.add_argument('--propID', nargs="+", default=[], help='specify proposal IDs (default=%(default)s)')
        parser.add_argument('-l', '--lookbacktime', type=float, default=None, help='TODO lookback time in days.')
        parser.add_argument('--filters', nargs="+", default=[], choices=list(self.filters.keys()), help='specify list of filters (default=%(default)s)')

        parser.add_argument('-d','--date_select', nargs="+", default=[], help='Specify date range (MJD or isot format) applied to "dateobs_center" column. If single value, then exact match. If single value has "+" or "-" at the end, then it is a lower and upper limit, respectively. Examples: 58400+, 58400-,2020-11-23+, 2020-11-23 2020-11-25  (default=%(default)s)')
        parser.add_argument('-e','--expnum_select', nargs="+", default=[], help='Specify EXPNUM range applied to "EXPNUM" column. If single value, then exact match. If single value has "+" or "-" at the end, then it is a lower and upper limit, respectively. If two values, then range. Examples: 385539+, 385539-, 385539 385600 (default=%(default)s)')
        parser.add_argument('-l','--expnum_list', nargs="+", default=[], help='Specify list of EXPNUM. examples: 385539 385600 385530 (default=%(default)s)')

        parser.add_argument('--tmpl', action='store_true', default=False, help='PHOTPIPE: designate the selected images as templates, i.e. the subdir will be "tmpl"')
        parser.add_argument('--deeplinkcheck', action='store_true', default=False, help='PHOTPIPE: perform a deep check if the links to the MEF are correct. This takes more time than the usual check')
        parser.add_argument('--clobberlinks', action='store_true', default=False, help='PHOTPIPE: clobber the links, and in addition make sure that there are no other leftover links in the subdirs. This takes extra time and in general is only needed when something major like tile boxsizes changes')

        parser.add_argument('--bad_detnames', nargs="+", default=['N30','S7'], help='specify bad detector names (default=%(default)s)')


        parser.add_argument('--imoutcols', nargs="+", default=None, help='Specify the columns of the image table to show when printing to screen or saving. If \'all\', then all columns are shown. If not specified, then the subset of columns defined in self.imoutcols_short are used.')
        
        parser.add_argument('--outrootdir', default=default_outrootdir, help='output root directory (default=%(default)s)')
        parser.add_argument('--ID2outsubdir', action='store_true', default=False, help='Add the fieldname to the output subdir. By default, IDcol is used as field column (default=%(default)s)')
        parser.add_argument('--info2filename', action='store_true', default=False, help='Rename filenames to the form field.YYMMDD.filter_ID (default=%(default)s)')

        parser.add_argument('--photpipe_outfilename', action='store_true', default=False, help='PHOTPIPE: Make the subdir structure photpipe compatible (subdir with the physical images is fieldname/mef, and images in tilenumber subdirs are linked to ../mef). Give filenames in the form field.YYMMDD.filter_ID. (default=%(default)s)')
        parser.add_argument('--photpipe_old_outfilename', action='store_true', default=False, help='PHOTPIPE: Make the subdir structure photpipe compatible to the OLD version of photpipe which had the images organized by extension number subdirs (subdir with the physical images is fieldname/mef, and images in 1-62 subdirs are linked to ../mef). Give filenames in the form field.YYMMDD.filter_ID. (default=%(default)s)')
        parser.add_argument('--eventpipe_outfilename', action='store_true', default=False, help='PHOTPIPE: Make the subdir structure eventpipe compatible (subdir with the physical images is fieldname/mef, and images in subdirs fieldname/<filter> are linked to ../mef). templates are in fieldname/tmpl/<filter>. Give filenames in the form field.YYMMDD.filter_ID. (default=%(default)s)')
        parser.add_argument('--image_quality', action='store_true', default=False, help='Get image quality columns for image table.')
        
        # These are only for when either --photpipe_outfilename or  --eventpipe_outfilename
        group_photpipe = parser.add_argument_group("options for Photpipe-compatible filenames. Only used if --photpipe_outfilename or --eventpipe_outfilename")
        group_photpipe.add_argument('--tilepattern', default='detector', 
                                    help='This is for matching detectors to tiles: set self.tile_boxsize_Dec \
                                    and self.tile_boxsize_RA according to thetilepattern used. \
                                    MAKE SURE self.tilepatternmode IS THE SAME THAT WAS USED TO CREATE THE FIELDCENTERS FILE! (default=%(default)s)')
        group_photpipe.add_argument('--tile_boxsize_RA', type=float, default=None, help='Overwrite the tile_boxsize_RA determined by --tilepattern (default=%(default)s)')
        group_photpipe.add_argument('--tile_boxsize_Dec', type=float, default=None, help='Overwrite the tile_boxsize_Dec determined by --tilepattern  (default=%(default)s)')
        group_photpipe.add_argument('--tile_boxsize_padding_arcsec', type=float, default=50.0, help='You can add extra padding to EACH side of the tiles,i.e. both tile_boxsize_* increase by 2xtile_boxsize_padding_arcsec (default=%(default)s)')
        group_photpipe.add_argument('--min_overlap_fraction', type=float, default=0.3, 
                                    help='the overlap fraction is calculated as the overlap area between \
                                    detector and tile, divided by the area of the detector. This means that \
                                    the overlap_fraction = 1.0 if the detector is fully within the tile. \
                                    a detecor images is included into a tile of the \
                                    overlap_fraction >= min_overlap_fraction  (default=%(default)s)')

        return(parser,group_photpipe)

    def add_RaDec_pointingtable(self,RaDecList,racol,deccol,IDlist=None):
        if self.IDcol is None: raise RuntimeError('self.IDcol needs to be defined!')
        if IDlist is None:
            IDlist = [f'Pos{x}' for x in range(1,len(RaDecList)+1)]
        else:
            if len(IDlist)!=len(RaDecList):
                raise RuntimeError("IDlist has %d entries, unequal the number of entries of Ra/Dec pairs: %d" % (len(IDlist),len(RaDecList)))

        for i in range(len(RaDecList)):
            print('Adding position {} {} to columns {} {}'.format(RaDecList[i][0],RaDecList[i][1],racol,deccol))
            dict={}
            dict[self.IDcol]=IDlist[i]
            dict[racol]=RaDecList[i][0]
            dict[deccol]=RaDecList[i][1]
            self.pointingtable.newrow(dict)

        self.racol=racol
        self.deccol=deccol

        # make sure the self.IDcol is copied from the pointing table to the image table
        if not (self.IDcol in self.pointing2im_columns):
            self.pointing2im_columns.append(self.IDcol)

        return(0)


    def load_pointingtable(self,pointingfilename,racol=None,deccol=None,**kwargs):
        self.pointingtable.load(pointingfilename,**kwargs)

        #Make sure racol and deccol exists! If not perfect match, try to see if there is a column that fits case-insensitive!
        if racol is not None:
            self.racol=None
            if racol in self.pointingtable.t.columns:
                self.racol = racol
            else:
                for col in self.pointingtable.t.columns:
                    if racol.lower() == col.lower():
                        if self.verbose>2:
                            print('WARNING! could not find racol %s, but %s seem to match, using it going forward!' % (racol,col))
                        self.racol=col
            if self.racol is None:
                raise RuntimeError("Could not find Ra column %s in pointingfile" % (racol))

        if deccol is not None:
            self.deccol=None
            if deccol in self.pointingtable.t.columns:
                self.deccol = deccol
            else:
                for col in self.pointingtable.t.columns:
                    if deccol.lower() == col.lower():
                        if self.verbose>2:
                            print('WARNING! could not find deccol %s, but %s seem to match, using it going forward!' % (deccol,col))
                        self.deccol=col
            if self.deccol is None:
                raise RuntimeError("Could not find Dec column %s in pointingfile" % (deccol))

        if self.verbose:
            print('%d entries in %s' % (len(self.pointingtable.t),pointingfilename))
        if self.verbose>2:
            print('\n### POINTING TABLE:')
            self.pointingtable.write()
        
        return(0)

    def ra_dec_box_search(self, ra, dec,
                          searchradius = 1.1*u.deg,
                          size=1.0, radius=0.3*u.deg,
                          imagequalityflag = False,
                          aux_columns_archive=None,
                          instrument=['decam'],
                          lookbacktime=None,
                          filt=None,
                          proc_type=['instcal'],
                          obs_type=[],
                          propID=[],
                          prod_type=['image'],
                          row_limit=40000):
        coord = parse_coord(ra, dec)
        ra = coord.ra.degree
        dec = coord.dec.degree


        # get the search radius!
        if searchradius is None:
            # default is the DECam FOV
            searchradius = 1.1*u.deg
        else:
            if type(searchradius) is type(list()):
                if len(searchradius)==1:
                    searchradius = float(searchradius[0])*u.deg
                elif len(searchradius)==2:
                    searchradius = float(searchradius[0])*u.Unit(searchradius[1])
                else:
                    raise RuntimeError('Cannot convert searchradius into physical units!')
        if searchradius.unit is u.deg:
            print(f'SEARCH RADIUS: {searchradius.value:0.004f} {searchradius.unit:s}')
        else:
            print(f'SEARCH RADIUS: {searchradius.value} {searchradius.unit:s} ({searchradius.to(u.deg):0.004f})')

        #apiurl = f'{self.adsurl}/fasearch/?limit={row_limit}'
        apiurl = f'{self.adsurl}/find/?limit={row_limit}'


        # define the box
        demin = coord.dec.degree-searchradius.to(u.deg).value
        demax = coord.dec.degree+searchradius.to(u.deg).value
        if demin<-90.0: demin=-90.0
        if demax>90.0: demax=90.0
        if demin==-90.0 or demax==90.0:
            ramin=0
            ramax=360.0
        else:
            costerm = min(np.cos(demin*np.pi/180.0),np.cos(demax*np.pi/180.0))
            ramin = coord.ra.degree-searchradius.to(u.deg).value*1./costerm
            ramax = coord.ra.degree+searchradius.to(u.deg).value*1./costerm
            if ramin<0: ramin+=360.0
            if ramax>360.0: ramax-=360.0

        # make list of columns to get
        cols = list(self.corecolumns.keys())

        # 09/22/2021: some gymnastics: the API is unhappy with EXPNUM etc under certain circumstances with stacked and projected
        # Sean McManu from NOIR says that this will be fixed in one of the next releases
        if len(AnotB(proc_type,['stacked','projected']))==0:
            # don't ask for these entries if only stacked and/or projected. It's ok if also asked for other proc_types!
            cols.remove('EXPNUM')
            if 'projected' in proc_type:
                cols.remove('OBJECT')
                cols.remove('EXPTIME')
        else:
            # if the list of proc_types is lead by either of ['stacked','projected'], then API barfs if asked for EXPNUM etc. Thus these proc_types need to be moved to the end
            if proc_type[0] in ['stacked','projected']:
                tmp = list(AandB(proc_type,['stacked','projected']))
                proc_type = list(AnotB(proc_type,['stacked','projected']))
                proc_type.extend(tmp)

        if aux_columns_archive is None: aux_columns_archive = self.aux_columns_archive
        if aux_columns_archive is not None:
            cols.extend(aux_columns_archive)


        jj_base={'outfields': cols,'search':[]}
        if instrument: jj_base['search'].append(['instrument']+instrument)
        if proc_type: jj_base['search'].append(['proc_type']+proc_type)
        if prod_type: jj_base['search'].append(['prod_type']+prod_type)
        if obs_type: jj_base['search'].append(['obs_type']+obs_type)
        if propID and (propID[0].lower()!='none'): jj_base['search'].append(['proposal']+propID)
        if filt is not None:
            filtnames = [self.filters[filt]]
            jj_base['search'].append(['ifilter']+filtnames)

        imtable = pdastroclass()

        if ramin>ramax:
            raise RuntimeError('This needs to be fixed!!')
            # Need to perform two searches to account for overlap
            jj=jj_base
            jj['search'].append(['ra_center',ramin,360.0])
            jj['search'].append(['dec_center',demin,demax])
            ads_df1 = pd.DataFrame(requests.post(apiurl,json=jj).json()[1:])
            ads_tb1 = Table.from_pandas(ads_df1)

            jj=jj_base
            jj['search'].append(['ra_center',0.0,ramax])
            jj['search'].append(['dec_center',demin,demax])
            ads_df2 = pd.DataFrame(requests.post(apiurl,json=jj).json()[1:])
            ads_tb2 = Table.from_pandas(ads_df2)

            ads_tb = vstack([ads_tb1,ads_tb2])

        else:
            jj=jj_base
            jj['search'].append(['ra_center',ramin,ramax])
            jj['search'].append(['dec_center',demin,demax])

            if self.verbose>2: print('jj_base:',jj_base)
            res = requests.post(apiurl,json=jj)
            res.raise_for_status()
            if self.verbose:
                #print(f'Search status={res.status_code} res={res.content}')
                print(f'Search status={res.status_code}')

            if res.status_code != 200:
                raise Exception(f'status={res.status_code} content={res.content}')

#            imtable.t = pd.DataFrame(requests.post(apiurl,json=jj).json()[1:])
            imtable.t = pd.DataFrame(res.json()[1:])

        if len(imtable.t)>0:

            imtable = self.sanitize_and_cut_table(imtable, coord, searchradius)

            # Get image quality information
            if imagequalityflag:
                if self.verbose: print('### Getting more info from the archive to determine image quality!!')
                imtable = self.calc_image_quality(imtable, jj_base, ramin,
                    ramax, demin, demax, coord,
                    # Use larger search radius to account for the fact that we're
                    # querying on pointing center of each array rather than DECam
                    searchradius=2*searchradius,
                    instrument=instrument,
                    lookbacktime=lookbacktime,
                    filt=filt,
                    proc_type=proc_type,
                    obs_type=obs_type,
                    propID=propID,
                    prod_type=prod_type)

            #imtable.write(columns=['ra_center','dec_center','EXPNUM','OBJECT','proposal','proc_type','prod_type','obs_type','dateobs_center'])
            if self.verbose>1: print('Columns in table:',imtable.t.columns)
            if self.verbose>1: print(imtable.t)

        return(imtable)

    # Moved table sanitization and search radius cut to a new function so it can
    # be used for image quality table
    def sanitize_and_cut_table(self, table, coord, searchradius, hdu=False):

        table.t['filt']=table.t['ifilter'].str.extract(r'(^\w+)\s+DECam')
        table.t['archive_filename']=table.t['archive_filename'].str.extract(r'.*\/(\S+)$')

        # Extract the NOIR suffix. This suffix is unique for a given proc_type and prod_type pair
        table.t['noirsuffix']=table.t['archive_filename'].str.extract(r'^\w+\_\w+\_\w+\_(o[a-z]+)')
        table.t['redversion']=table.t['archive_filename'].str.extract(r'\_o[a-z]+\_[a-zA-Z]+\_(\w+)\.fits\.fz')


        # some of the first DECam data do not have the current filename
        # convention. Trying to fix it!
        ix_null = table.ix_is_null('noirsuffix')
        for ix in ix_null:
            noirsuffix=''
            if table.t.loc[ix,'proc_type'] == 'instcal':
                noirsuffix = 'oo'
            elif table.t.loc[ix,'proc_type'] == 'stacked':
                noirsuffix = 'os'
            else:
                raise RuntimeError("product {table.t.loc[ix,'archive_filename']} seems to have the old filename convention, and cannot fix it for proc_type={table.t.loc[ix,'proc_type']} yet! needs to be implemented (should be easy!)")
            if table.t.loc[ix,'prod_type'] == 'image':
                noirsuffix += 'i'
            elif table.t.loc[ix,'prod_type'] == 'dqmask':
                    noirsuffix += 'd'
            elif table.t.loc[ix,'prod_type'] == 'wtmap':
                noirsuffix += 'w'
            else:
                raise RuntimeError("product {table.t.loc[ix,'archive_filename']} seems to have the old filename convention, and cannot fix it for prod_type={table.t.loc[ix,'prod_type']} yet! needs to be implemented (should be easy!)")
            table.t.loc[ix,'noirsuffix'] = noirsuffix

            pass

        # calculate the separation between pointing position and product position
        if hdu:
            table.t['sep'] = coord.separation(SkyCoord(list(table.t['hdu:ra_center']),list(table.t['hdu:dec_center']), unit=(u.deg, u.deg), frame='icrs')).deg
            ixs_withinradius = table.ix_inrange('sep',None,searchradius.to(u.deg).value)

            ixs_sorted = table.ix_sort_by_cols(['dateobs_center','proc_type','prod_type'],indices=ixs_withinradius)
            table.t=table.t.loc[ixs_sorted].reset_index(drop=True)

            for col in self.image_quality_columns:
                if col in table.t.columns:
                    table.t[col]=table.t[col].astype(self.image_quality_columns[col])
        else:
            table.t['sep'] = coord.separation(SkyCoord(list(table.t['ra_center']),list(table.t['dec_center']), unit=(u.deg, u.deg), frame='icrs')).deg
            ixs_withinradius = table.ix_inrange('sep',None,searchradius.to(u.deg).value)

            ixs_sorted = table.ix_sort_by_cols(['dateobs_center','proc_type','prod_type'],indices=ixs_withinradius)
            table.t=table.t.loc[ixs_sorted].reset_index(drop=True)

            for col in self.corecolumns:
                if col in table.t.columns:
                    table.t[col]=table.t[col].astype(self.corecolumns[col])

        return(table)

    def calc_image_quality(self, table, jj_base, ramin, ramax, demin, demax,
        coord,
        searchradius = 1.1*u.deg,
        instrument=['decam'],
        lookbacktime=None,
        filt=None,
        proc_type=['instcal'],
        obs_type=[],
        propID=[],
        prod_type=['image'],
        row_limit=40000):

        imqtable = pdastroclass()

        # Create dummy columns
        table.t['FWHM'] = [None]*len(table.t)
        table.t['M5SIGMA'] = [None]*len(table.t)

        cols = list(self.image_quality_columns.keys())
        jj_base={'outfields': cols,'search':[]}
        if instrument: jj_base['search'].append(['instrument']+instrument)
        if proc_type: jj_base['search'].append(['proc_type']+proc_type)
        if prod_type: jj_base['search'].append(['prod_type']+prod_type)
        if obs_type: jj_base['search'].append(['obs_type']+obs_type)
        if propID and (propID[0].lower()!='none'): jj_base['search'].append(['proposal']+propID)
        if filt is not None:
            filtnames = [self.filters[filt]]
            jj_base['search'].append(['ifilter']+filtnames)

        apiurl = f'{self.adsurl}/find/?limit={row_limit}&rectype=hdu'

        if ramin>ramax:
            raise RuntimeError('This needs to be fixed!!')
            # Need to perform two searches to account for overlap
            jj=jj_base
            jj['search'].append(['hdu:ra_center',ramin,360.0])
            jj['search'].append(['hdu:dec_center',demin,demax])
            ads_df1 = pd.DataFrame(requests.post(apiurl,json=jj).json()[1:])
            ads_tb1 = Table.from_pandas(ads_df1)

            jj=jj_base
            jj['search'].append(['hdu:ra_center',0.0,ramax])
            jj['search'].append(['hdu:dec_center',demin,demax])
            ads_df2 = pd.DataFrame(requests.post(apiurl,json=jj).json()[1:])
            ads_tb2 = Table.from_pandas(ads_df2)

            imqtable.t = vstack([ads_tb1,ads_tb2])

        else:
            jj=jj_base
            jj['search'].append(['hdu:ra_center',ramin,ramax])
            jj['search'].append(['hdu:dec_center',demin,demax])

            if self.verbose>2: print('jj_base:',jj_base)
            res = requests.post(apiurl,json=jj)
            res.raise_for_status()
            if self.verbose:
                print(f'Search status={res.status_code}')

            if res.status_code != 200:
                raise Exception(f'status={res.status_code} content={res.content}')

            imqtable.t = pd.DataFrame(res.json()[1:])

        if len(imqtable.t)>0:
            imqtable = self.sanitize_and_cut_table(imqtable, coord, searchradius, hdu=True)

            # Get only image data, which will have image quality info
            immask = table.t['prod_type']=='image'

            for i,row in table.t[immask].iterrows():
                # Match by EXPNUM, which should be unique for each image
                mask = imqtable.t['EXPNUM']==row['EXPNUM']
                # Average FWHM
                fwhm = imqtable.t[mask]['hdu:FWHM']
                fwhm = fwhm.replace(0, np.NaN)
                mean_fwhm = fwhm.mean()
                # Get average M5SIGMA value
                Npix_per_FWHM_Area = 2.5 * 2.5 * imqtable.t[mask]['hdu:FWHM']**2
                skysig_per_FWHM_Area = np.sqrt(Npix_per_FWHM_Area * imqtable.t[mask]['hdu:AVSIG']**2)
                m5sigma = -2.5 * np.log10(5.0 * skysig_per_FWHM_Area) + imqtable.t[mask]['MAGZERO']
                m5sigma = m5sigma.replace(0, np.NaN)
                mean_m5sigma = m5sigma.mean()

                for ix in np.where(table.t['EXPNUM']==row['EXPNUM'])[0]:
                    table.t['FWHM'][ix]=mean_fwhm
                    table.t['M5SIGMA'][ix]=mean_m5sigma
            self.image_quality=True

        return(table)
    
    def get_depth_estimate(self,indices = None):
        sys.exit(0)
                
        ixs = self.getindices(indices = indices)
        for ix in ixs:
            apiurl = f"{self.apiheader}/{self.t.loc[ix,'md5sum']}/"
            print('CCCCCCCCCCC',apiurl)
            dat = download_file(apiurl, cache=False, show_progress=True,timeout=30, http_headers=dict(Authorization=self.token))
            print('VVVV',dat)
            testfilename='/Users/arest/delme/test1.txt'
            print(testfilename)
            shutil.move(dat, testfilename)
            sys.exit(0)

            hdr = fits.getheader(dat)
            print('VVVV',hdr)
            sys.exit(0)

            res = requests.post(apiurl)
            res.raise_for_status()
            if self.verbose:
                #print(f'Search status={res.status_code} res={res.content}')
                print(f'Search status={res.status_code}')

            if res.status_code != 200:
                raise Exception(f'status={res.status_code} content={res.content}')
            else:
                print(f"SUCCESSSS!!!!!!!\n{res.content}")

            sys.exit(0)
            
    def pointingtable_selectrange(self,col,select_exp,indices=None):
        # parse trailing '+' and '-', and get limits
        limits = getlimits(select_exp)
        if limits is None: return(indices)
        
        ixs = self.pointingtable.getindices(indices=indices)
        ixs = self.pointingtable.ix_not_null(col,indices=ixs)

        # get the type right
        if is_float_dtype(self.pointingtable.t[col]) or is_integer_dtype(self.pointingtable.t[col]):
            for i in (0,1):
                if limits[i] is not None:
                    if is_float_dtype(self.pointingtable.t[col]): limits[i]=float(limits[i])
                    if is_integer_dtype(self.pointingtable.t[col]): limits[i]=int(limits[i])
        
        ixs_keep = self.pointingtable.ix_inrange(col,limits[0],limits[1],indices=ixs)
        print(f'{col} cut {limits[0]} - {limits[1]}: keeping {len(ixs_keep)} from {len(ixs)}')
        return(ixs_keep)

    def pointingtable_selectlist(self,col,valuelist,indices=None):
        if (valuelist is None) or len(valuelist)==0:
            return(indices)

        ixs = self.pointingtable.getindices(indices=indices)
        ixs = self.pointingtable.ix_not_null(col,indices=ixs)
        
 

        ixs_keep=[]
        for i in range(len(valuelist)):
            if is_float_dtype(self.pointingtable.t[col]): valuelist[i]=float(valuelist[i])
            if is_integer_dtype(self.pointingtable.t[col]): valuelist[i]=int(valuelist[i])
            ixs_keep.extend(self.pointingtable.ix_equal(col,valuelist[i],indices=ixs))
        ixs_keep=unique(ixs_keep)
        
        print(f'{col} list cut: keeping {len(ixs_keep)} from {len(ixs)}')
        return(ixs_keep)


    def date_select(self,date_select,indices=None):
        ixs=self.getindices(indices=indices)

        # parse trailing '+' and '-', and get limits
        limits = getlimits(date_select)
        if limits is None: return(ixs)

        # Convert MJD into dates if necessary
        for i in (0,1):
            if limits[i] is not None:
                try:
                    mjd = float(limits[i])
                    limits[i]= Time(mjd, format='mjd').to_value('isot')
                except:
                    limits[i]= Time(limits[i]).to_value('isot')

        ixs_keep = self.ix_inrange('dateobs_center',limits[0],limits[1],indices=ixs)
        print(f'date range cut {limits[0]} - {limits[1]}: keeping {len(ixs_keep)} from {len(ixs)}')
        return(ixs_keep)

    def expnum_select(self,expnum_select,indices=None):
        ixs=self.getindices(indices=indices)
        # parse trailing '+' and '-', and get limits
        limits = getlimits(expnum_select)
        if limits is None:
            return(ixs)

        for i in range(len(limits)):
            if limits[i] is not None: limits[i]=int(limits[i])

        ixs = self.ix_remove_null('EXPNUM',indices=ixs)
        ixs_keep = self.ix_inrange('EXPNUM',limits[0],limits[1],indices=ixs)
        print(f'expnum cut {limits[0]} - {limits[1]}: keeping {len(ixs_keep)} from {len(ixs)}')
        return(ixs_keep)

    def expnum_list(self,expnum_list,indices=None):
        ixs=self.getindices(indices=indices)
        if expnum_list is None or len(expnum_list)==0:
            return(ixs)

        ixs_keep = []
        for expnum in expnum_list:
            expnum = int(expnum)
            ixs2add = self.ix_equal('EXPNUM',expnum,indices=ixs)
            ixs_keep.extend(ixs2add)
        print(f'expnum list cut: keeping {len(ixs_keep)} from {len(ixs)}')
        return(ixs_keep)

    def filter_select(self,filterlist,indices=None):

        ixs=self.getindices(indices=indices)
        if filterlist is None or len(filterlist)==0:
            return(ixs)

        ixs_keep = []
        for filt in filterlist:
            ixs2add = self.ix_equal('filt',filt,indices=ixs)
            ixs_keep.extend(ixs2add)
        print(f'filter list cut: keeping {len(ixs_keep)} from {len(ixs)}')
        return(ixs_keep)



    def find_images_all_pointings(self,
                                indices=None,
                                searchradius=None,
                                pointingtable=None,
                                racol = None,
                                deccol = None,
                                imagequalityflag = False,
#                                fieldcol = None,
#                                outfieldcol = None,
                                pointing2im_columns=[],
                                aux_columns_archive=[],
                                lookbacktime=None,
                                filt=None,
                                proc_type=[],
                                prod_type=[],
                                obs_type=[],
                                propID=[],
                                imoutcols=None):

        if pointingtable is None: pointingtable=self.pointingtable
        if racol is None: racol=self.racol
        if deccol is None: deccol=self.deccol
#        if fieldcol is None: fieldcol=self.fieldcol
#        if outfieldcol is None: outfieldcol=self.outfieldcol

        pointing2im_columns.extend(self.pointing2im_columns)


        ixs=pointingtable.getindices(indices=indices)
        #pointingtable.t['Nim'] = None
        #pointingtable.t['Nexist'] = None
        for ix in ixs:
            #s = '\n########################\n### Checking available data for {}={} at RA={}, Dec={}'.format(fieldcol,pointingtable.t.loc[ix,fieldcol],pointingtable.t.loc[ix,racol],pointingtable.t.loc[ix,deccol])
            print('\n###########################################################\n### Checking available products at RA={}, Dec={}'.format(pointingtable.t.loc[ix,racol],pointingtable.t.loc[ix,deccol]))
            if self.verbose:
                print(pointingtable.t.iloc[ix:ix+1])
            imtable = self.ra_dec_box_search(pointingtable.t.loc[ix,racol],pointingtable.t.loc[ix,deccol],
                                             searchradius=searchradius,
                                             imagequalityflag=imagequalityflag,
                                             aux_columns_archive=aux_columns_archive,
                                             lookbacktime=lookbacktime,
                                             filt=filt,
                                             proc_type=proc_type,
                                             prod_type=prod_type,
                                             obs_type=obs_type,
                                             propID=propID)

            # concat the image table to the main table.
            if len(imtable.t)>0:
                # copy info from pointing table to image table
                for col in pointing2im_columns:
                    imtable.t[col] = pointingtable.t.loc[ix,col]

                if len(self.t)>0:
                    self.t = pd.concat([self.t,imtable.t],ignore_index=True)
                else:
                    self.t = copy.deepcopy(imtable.t)

                print('{} products found!'.format(len(self.t)))
            else:
                print('WARNING: No products found!')

        ##################
        # get the outputcolumns!

        # make sure they are in the preferred order, and put the key ones first
        self.imoutcols=[]
        self.imoutcols.extend(copy.deepcopy(pointing2im_columns))
        self.imoutcols.extend(['EXPNUM','OBJECT','filt','EXPTIME','sep'])
        if self.image_quality: 
            self.imoutcols.extend(['FWHM','M5SIGMA'])
            self.default_formatters['FWHM']='{:.2f}'.format
            self.default_formatters['M5SIGMA']='{:.2f}'.format
        self.imoutcols.extend(aux_columns_archive)
        

        # imoutcols == None: use the short list of columns defined in self.imoutcols_short
        # imoutcols == 'all': use all columns
        # imoutcols is list of columns: add it to self.imoutcols
        if imoutcols is None:
            self.imoutcols.extend(AnotB(self.imoutcols_short,self.imoutcols,keeporder=True))
        elif imoutcols[0].lower()=='all':
            self.imoutcols.extend(AnotB(self.t.columns,self.imoutcols,keeporder=True))
        else:
            self.imoutcols.extend(AnotB(imoutcols,self.imoutcols,keeporder=True))

        # remove columns that are not necessary
        self.imoutcols = AnotB(self.imoutcols,['instrument','telescope','ifilter'],keeporder=True)

        badcols = AnotB(self.imoutcols,self.t.columns)
        if len(badcols)>0:
            print(f"Warning! There are output columns that are not in the table: {''.join(badcols)}")

        # make sure no columns are in there that do not exist!
        self.imoutcols = AandB(self.imoutcols,self.t.columns,keeporder=True)

        return(0)
    
    def mk_outfilename(self, ix, IDcol=None, outrootdir=None, 
                       photpipe_outfilename=False, 
                       eventpipe_outfilename=False, 
                       tmpl=False,
                       ID2outsubdir=False, info2filename=False,
                       skip_check_if_outfile_exists=False):
        outdir = outrootdir.rstrip("/")

        if IDcol is not None:
            ID = self.t.loc[ix,IDcol]
        else:
            ID = None

        # Replace spaces and special characters from ID with '_', we don't want to have them in the filename
        if ID is not None:
            ID=str(ID)
            ID=re.sub('\s+|\\|\,|\#|\$|\%|\&|\*','_',ID)
        

        if photpipe_outfilename or eventpipe_outfilename or ID2outsubdir:
            if ID is None:
                if IDcol is None:
                    raise RuntimeError("No ID column is specified, cannot add ID to filename!")
                else:
                    raise RuntimeError("Value of ID column {} is None! Cannot determine output filename".format(IDcol))                  
            if tmpl:
                if eventpipe_outfilename:
                    outdir += f'/{ID}/tmpl'
                else:
                    outdir += '/tmpl'
            else:
                outdir += f'/{ID}'

        if photpipe_outfilename or eventpipe_outfilename:
            outdir += '/mef'

        if photpipe_outfilename or eventpipe_outfilename or info2filename:
            t = Time(self.t.loc[ix,'dateobs_center'])
            #t = Time('2021-10-24T00:00:30', format='isot')
            m = re.search('^\d\d(\d\d)\-(\d\d)\-(\d\d)T',t.to_value('isot'))
            if m is not None:
                YYMMDD = ''.join(m.groups())
            else:
                raise RuntimeError('Could not parse {} for YYMMDD'.format(t.to_value('isot')))
            outfilename = '{}.{}'.format(ID,YYMMDD)
            
            if not('EXPNUM' in self.t.columns) or self.t.loc[ix,'EXPNUM'] is pd.NA:
                # give images without a EXPNUM a dummy 0 value
                outfilename += '.0'
            else:
                outfilename += '.{}'.format(self.t.loc[ix,'EXPNUM'])

            # get the suffix. If possible, use the one from the archive_filename. However,
            # some of the first images have a different filename convention, then 'nan' is inserted
            m = re.search(f'(_{self.t.loc[ix,"noirsuffix"]}_.*)',self.t.loc[ix,'archive_filename'])
            if m is not None:
                fullsuffix = m.groups()[0]
            else:
                fullsuffix = f'_{self.t.loc[ix,"noirsuffix"]}_{self.t.loc[ix,"filt"]}.fits.fz'
            outfilename+= fullsuffix
        else:
            outfilename = self.t.loc[ix,'archive_filename']

        fullfilename = '{}/{}'.format(outdir,outfilename)
        self.t.loc[ix,'outfilename']=fullfilename

        if not skip_check_if_outfile_exists:
            if os.path.exists(fullfilename):
                self.t.loc[ix,'dl_code'] = 2
                self.t.loc[ix,'dl_str'] = 'exists'
            else:
                self.t.loc[ix,'dl_code'] = 0
                self.t.loc[ix,'dl_str'] = None

    def mk_outfilenames(self,indices = None, 
                        IDcol=None,
                        outrootdir=None, 
                        photpipe_outfilename=False, 
                        eventpipe_outfilename=False, 
                        tmpl=False,
                        ID2outsubdir=False, 
                        info2filename=False,
                        skip_check_if_outfile_exists=False):
        
        # By default, use the IDcol as IDcol
        if IDcol is None:
            IDcol = self.IDcol
        
        ixs = self.getindices(indices = indices)
        self.t.loc[ixs,'outfilename'] = None
        self.t.loc[ixs,'dl_code'] = np.nan
        self.t.loc[ixs,'dl_str'] = None
        self.t['dl_code'] = self.t['dl_code'].astype(pd.Int32Dtype())
        if 'outfilename' not in self.imoutcols: self.imoutcols.append('outfilename')
        if 'dl_code' not in self.imoutcols: self.imoutcols.append('dl_code')
        if 'dl_str' not in self.imoutcols: self.imoutcols.append('dl_str')
        for ix in ixs:
            self.mk_outfilename(ix, IDcol=IDcol, outrootdir=outrootdir, 
                                photpipe_outfilename=photpipe_outfilename, 
                                eventpipe_outfilename=eventpipe_outfilename, 
                                tmpl=tmpl,
                                ID2outsubdir=ID2outsubdir, info2filename=info2filename, 
                                skip_check_if_outfile_exists=skip_check_if_outfile_exists)
        return(0)

    def download_product_requests(self, url, outfilename, token):
        print(f'Dowloading file {url} with login, this might take a few minutes! Starting download at UT={Time.now()}')
        if isinstance(self.token, list) and len(self.token)>0:
            self.token = self.token[0]

        res = requests.get(url, headers=dict(Authorization=self.token))
        try:
            res.raise_for_status()
        except Exception as e:
            msg = str(e)
            print(f'ERROR: for file {outfilename}: {msg}')
            return(7,'ERRORdownload')
        
        if self.verbose>1: print(f'Saving file to {outfilename}')
        with open(outfilename,'wb') as fitssave:
            fitssave.write(res.content)

        if not os.path.isfile(outfilename):
            print(f'ERROR: {outfilename} does not exist!!')
            return(9,'ERRORnotexist')           

        return(1,'downloaded')

    def download_product(self, ix_im, token = None, clobber=False):
        """
        Download the product of entry with index ix_im in self.t
        
        Parameters
        ----------
        ix_im : integer
            index for the self.t entry.
        token : string, optional
            optional token. If not passed, then self.token is used. If
            self.token is also None, then attempt to download without login
        clobber : boolean, optional
            Re-download even if exists.

        Returns
        -------
        dlcode,dlstr:
            0,None: file does not exist
            1,'downloaded': file was succesfully downloaded
            2,'exists':     file already exists, skipped
            3,'ERRORNone':  outfilemame is None
            4,'ERRORempty': outfilemame is empty string
            5,'ERRORmd5sum':md5sum is not an avialable column
            6,'ERRORdel':   file could not be removed before download
            7,'ERRORdownload': Error during download
            8,'ERRORsaving':Error when saving the downloaded file
            9,'ERRORnotexist': After teh file was downloaded and saved, it doesn't exist
        """
        outfilename = self.t.loc[ix_im,'outfilename']
        if outfilename is None:
            print('ERROR: outfilename is None!')
            return(3,'ERRORNone')
        if outfilename=='':
            print('ERROR: outfilename is empty string!')
            return(4,'ERRORempty')

        if os.path.exists(outfilename) and not clobber:
            print(f'WARNING: {outfilename} exists and clobber=False, thus skipping re-downloading it!')
            return(2,'exists')

        if self.verbose>1:print(f'Downloading to {outfilename}')
        makepath4file(outfilename)

        if 'md5sum' not in self.t.columns:
            w='ERROR: cannot download without md5sum in '+\
                'search_columns'
            print(w)
            return(5,'ERRORmd5sum')
        else:
            #url = self.t.loc[ix_im,'url']
            url = self.apiretrieve + '/' + self.t.loc[ix_im,'md5sum'] + '/'
            
        if rmfile(outfilename,raiseError=False):
            print('ERROR: could not remove old file {outfilename}')
            return(6,'ERRORdel')
        
        tstart = Time.now()
        print(f'Dowloading file {url}')
        
        try:
            if token is None:                
                dat = download_file(url, cache=False, show_progress=True,timeout=30)
            else:
                if isinstance(self.token, list) and len(self.token)>0:
                    self.token = self.token[0]
                dat = download_file(url, cache=False, show_progress=True,timeout=30, http_headers=dict(Authorization=self.token))
        except Exception as e:
            msg = str(e)
            print(f'ERROR: for file {outfilename}: {msg}')
            return(7,'ERRORdownload')

        if self.verbose>1: print(f'Saving file to {outfilename}')
        try:
            shutil.move(dat, outfilename)
        except Exception as err:
            print(f'ERROR: for file {outfilename}: {err}')
            return(8,'ERRORsaving')  
         
        if not os.path.isfile(outfilename):
            print(f'ERROR: {outfilename} does not exist!!')
            return(9,'ERRORnotexist')           

        tend = Time.now()
        print('time passed for download process: {:.2f} seconds'.format((tend-tstart).to_value('sec')))

        return(1,'downloaded')

    def check4doubleentries(self,indices=None, noirsuffix = 'ooi', preferredversion=['ls11','ls10','ls9','ls8','ls7','v3','v2','v1','d3','d2','d1','a3','a2','a1']):
        indices = self.getindices(indices=indices)
        ixs_suffix = self.ix_equal('noirsuffix',noirsuffix,indices=indices)
        (dupl,) = np.where(self.t.loc[ixs_suffix,'EXPNUM'].duplicated(keep=False))
        ixs_dupl = ixs_suffix[dupl]
        if len(ixs_dupl)>0:
            print(f'WARNING!! There are different versions for the same noirsuffix={noirsuffix} image for {len(ixs_dupl)} images!')
            self.write(columns=self.imoutcols,indices=ixs_dupl)
            ixs_remove_all=[]
            
            duplicate_expnum = unique(self.t.loc[ixs_dupl,'EXPNUM'])
            duplicate_expnum.sort()
            for expnum in duplicate_expnum:
                # these are the indices of all entries with this exposure number
                ixs_expnum = self.ix_equal('EXPNUM',expnum,indices=indices)
                # these are the indices of all entries with noirsuffix and this exposure number
                ixs_expnum_suffix = self.ix_equal('EXPNUM',expnum,indices=ixs_suffix)
                versions = unique(self.t.loc[ixs_expnum_suffix,'redversion'])
                A = AandB(preferredversion,versions,keeporder=True)
                if len(A)>0:
                    keepversion=A[0]
                    #print('BBB',expnum,versions,keepversion)
                    ixs_remove = AnotB(ixs_expnum,self.ix_equal('redversion',keepversion,indices=ixs_expnum))
                    ixs_remove_all.extend(ixs_remove)
                    #self.write(columns=self.imoutcols,indices=ixs_remove)
                else:
                    raise RuntimeError(f'versions={versions} are not in preferred versions={preferredversion}, they need to be updated??')                    
            ixs_keep_all = AnotB(indices,ixs_remove_all)
            return(ixs_keep_all)
        else:
            return(indices)

    def download_products(self, indices=None, clobber=False, token=None, skip_confirm_download=True):
        # use token if available
        if token is None:
            token = self.token
        
        ixs = self.getindices(indices=indices)
        if 'dl_code' not in self.imoutcols: self.imoutcols.append('dl_code')
        if 'dl_str' not in self.imoutcols: self.imoutcols.append('dl_str')
        
        ixs_exist = self.ix_equal('dl_code',2,indices = ixs)
        if not clobber:
            ixs_download = AnotB(ixs,ixs_exist)
            print(f'\n###############################\n### Downloading {len(ixs_download)} files')
            if len(ixs_exist)>0: print(f'### skipping {len(ixs_exist)} since they already exist')
        else:
            ixs_download = ixs
            print(f'\n###############################\n### Downloading {len(ixs_download)} files')
            if len(ixs_exist)>0: print(f'### clobbering {len(ixs_exist)} that already exist')
        
        if len(ixs_download)==0:
            print('\n### NO PRODUCTS TO DOWNLOAD!\n###############################')
            return(0,ixs_download)    
            
        
        if not skip_confirm_download:
            do_it = input('Do you want to continue and download these products [y/n]?  ')
            if do_it.lower() in ['y','yes']:
                pass
            elif do_it.lower() in ['n','no']:
                print('OK, stopping....')
                sys.exit(0)
            else:
                print(f'Hmm, \'{do_it}\' is neither yes or no. Don\'t know what to do, so stopping ....')
                sys.exit(0)
                
        counter = 1
        successcounter=0
        failedcounter=0
        for ix in ixs_download:
            print(f'\n### Downloading #{counter} out of {len(ixs_download)} files (status: {successcounter} successful, {failedcounter} failed): {os.path.basename(self.t.loc[ix,"outfilename"])}')
            (dl_code,dl_str) = self.download_product(ix, clobber=clobber, token=token)
            self.t.loc[ix,'dl_code']=dl_code
            self.t.loc[ix,'dl_str']=dl_str
            if dl_code<=2:
                successcounter+=1
            else:
                failedcounter+=1
            counter+=1
        
        print(f'\n### Download complete: {successcounter} successful, {failedcounter} failed\n###############################')
        return(0,ixs_download)    
        
    def linkfiles(self, fullname, relname, linkname, clobber=False, deeplinkcheck=False):
        if os.path.islink(linkname):
            if (not deeplinkcheck) and (not clobber):
                return(1,'exists')
            linkedfile = os.path.realpath(linkname)
            if not os.path.isfile(fullname):
                os.unlink(linkname)
                print(f'ERROR: mef {fullname} does not exist')
                return(5,'ERRORmefnotexists')
            if clobber or (not filecmp.cmp(linkedfile,fullname,shallow=False)):
                os.unlink(linkname)
                if os.path.islink(linkname):
                    print(f'ERROR: Could not unlink old link {linkname}')
                    return(2,'ERRORunlink')
            else:
                return(1,'exists')                   
        elif os.path.isfile(linkname):
            print('WARNING: the file {linkname} exists and is not a link! That should not be...')
            os.unlink(linkname)
            if os.path.isfile(linkname):
                print(f'ERROR: Could not remove old file {linkname}')
                return(3,'ERRORremove')
               
        if not os.path.isfile(fullname):
            return(5,'ERRORmefnotexists')
        makepath4file(linkname)
        os.symlink(relname,linkname)
        if not os.path.islink(linkname):
            print(f'ERROR: Could not link {linkname} to {relname}')
            return(4,'ERRORlink')
        return(0,'success')
 
    def make_and_check_photpipe_old_links(self, indices=None, 
#                                          photpipe_old_outfilename=False,
#                                          eventpipe_outfilename=False, 
                                          badamps=[35,61], Nccds=62, 
                                          clobber=False, deeplinkcheck=False):
        print(f'\n### making OLD-STYLE photpipe links... clobber:{clobber} deeplinkcheck:{deeplinkcheck}')

        ixs = self.getindices(indices=indices)
        self.t.loc[ixs,'linked']='-'
        if 'linked' not in self.imoutcols: self.imoutcols.append('linked')

        for ix in ixs:
            if self.t.loc[ix,'outfilename'] is None:
                continue
            if self.t.loc[ix,'noirsuffix']!='ooi' and self.t.loc[ix_im,'noirsuffix']!='osi' and self.t.loc[ix_im,'noirsuffix']!='osj' :
                continue
            if self.verbose>1: print('Checking/making links for',self.t.loc[ix,'outfilename'] )
            
            
            (dirname,filename)=os.path.split(self.t.loc[ix,'outfilename'])
            relname = f'../mef/{filename}'
            dirname=re.sub('\/$','',dirname)
            if re.search('\/mef$',dirname) is None:
                raise RuntimeError(f'Somethings is wrong, {dirname} should have \'mef\' subdir!')
            dirname=re.sub('\/mef$','',dirname)
            filename = re.sub('\.fits\.fz$','',filename)
            self.t.loc[ix,'linked']='success'
#            if eventpipe_outfilename:
#                linkname = f'{dirname}/{self.t.loc[ix,"filt"]}/{filename}.fits.fz'
#                (successcode,successstr)=linkfiles(self.t.loc[ix,'outfilename'],relname,linkname, clobber=clobber, deeplinkcheck=deeplinkcheck)
#                self.t.loc[ix,'linked']=successstr
#            else:
            for ccd in range(1,Nccds+1):
                if ccd in badamps:
                    continue
                linkname = f'{dirname}/{ccd}/{filename}_{ccd}.fits.fz'
                (successcode,successstr)=self.linkfiles(self.t.loc[ix,'outfilename'],relname,linkname, clobber=clobber, deeplinkcheck=deeplinkcheck)
                self.t.loc[ix,'linked']=successstr
        return(0)
    
    
    def make_and_check_photpipe_links(self, 
                                      indices=None, 
                                      tile_boxsize_RA=None, 
                                      tile_boxsize_Dec=None,
                                      min_overlap_fraction=0.5,
                                      fieldcenter_file=None,
                                      bad_detnames=[],
                                      clobberlinks=False, 
                                      deeplinkcheck=False):
        
        print(f'\n### making photpipe links... clobberlinks:{clobberlinks} deeplinkcheck:{deeplinkcheck}')
 
        # Make sure the tile boxesizes are defined!
        if tile_boxsize_RA is None: tile_boxsize_RA=self.tile_boxsize_RA
        if tile_boxsize_Dec is None: tile_boxsize_Dec=self.tile_boxsize_Dec
        if tile_boxsize_RA is None or tile_boxsize_Dec is None:
            raise RuntimeError(f'tile_boxsize_RA and/or tile_boxsize_Dec cannot be None! ({tile_boxsize_RA},{tile_boxsize_Dec})') 
            
        #first, get the tilepattern for detectors, in order to get the offsets to add to the positions
        from tilepattern import tilepatternclass          
        detectoroffsets=tilepatternclass()
        detectoroffsets.load_tilepattern('detector')
        # remove bad detectors
        print('BAD DETNAMES:',bad_detnames)

        if len(bad_detnames)>0:
            bad_ixs = []
            for bad_detname in bad_detnames:
                bad_ixs.extend(detectoroffsets.ix_equal('detname',bad_detname))
            print(f'NOTE: Dropping bad_detnames={bad_detnames} from detector list:')
            detectoroffsets.write(indices=bad_ixs)
            detectoroffsets.t.drop(index=bad_ixs,inplace=True)
        tilenumbers = detectoroffsets.getindices()
        
        # Also get the fieldcentersfile
        from fieldcenter import fieldcenterclass
        if fieldcenter_file is None: raise RuntimeError('The fieldcenters file needs to be specified!')
        fieldcenters = fieldcenterclass()
        fieldcenters.loadfieldcentersfile(fieldcenter_file)
        
        # Make sure the collumns are decimal degrees and save the SkyCoords into __coord__ column
        #fieldcenters.assert_radec_cols_decimal_degrees('RAdeg','DECdeg',coordcol='__coord__')

        ixs_im = self.getindices(indices=indices)
        if len(ixs_im)==0:
            print('WARNING! Nothing to link!')
            return(0)
        self.t.loc[ixs_im,'linked']='-'
        if 'linked' not in self.imoutcols: self.imoutcols.append('linked')
        #self.write(indices=ixs_im,columns=self.imoutcols)

        # for all RA,Dec of all products, get the SkyCoord into the __coord__ column
        self.assert_radec_cols_decimal_degrees('ra_center','dec_center',coordcol='__coord__',indices=ixs_im)
        #self.write(indices=ixs_im,columns=['ra_center','dec_center','__coord__'])

        # This is the max separation in RA and Dec between the fieldcenter and the detector centers to have any overlap
        max_separation_RA = 0.5*(self.detector_boxsize_RA + self.tile_boxsize_RA)
        max_separation_Dec = 0.5*(self.detector_boxsize_Dec + self.tile_boxsize_Dec)

        # Loop through all images
        for ix_im in ixs_im:
            print('*******%%%%%%%$$$$$$$$$******')
            print(self.t.loc[ix_im,'outfilename'])
            print(self.t.loc[ix_im,'noirsuffix'])
            print('*******%%%%%%%$$$$$$$$$******')
            if self.t.loc[ix_im,'outfilename'] is None:
                continue
            # skip noise and mask image
            if self.t.loc[ix_im,'noirsuffix']!='ooi' and self.t.loc[ix_im,'noirsuffix']!='osi' and self.t.loc[ix_im,'noirsuffix']!='osj':
                continue
            
            if self.verbose: print(f'Checking/making links for {self.t.loc[ix_im,"outfilename"]} at RA/Dec = {self.t.loc[ix_im,"ra_center"]:.5f},{self.t.loc[ix_im,"dec_center"]:.5f}')
            
            # get the center coordinate of the image
            coord = self.t.loc[ix_im,'__coord__']
            # and tile coords has the center of each detector for the given image
            detector_coords = coord.spherical_offsets_by(detectoroffsets.t.loc[tilenumbers,'dra']*u.deg,
                                                         detectoroffsets.t.loc[tilenumbers,'ddec']*u.deg)
            detectoroffsets.t['RA_detector']=detector_coords.ra.degree
            detectoroffsets.t['Dec_detector']=detector_coords.dec.degree

            # get all field centers for the given field from the fieldcenters file
            ixs_fieldcenter = fieldcenters.ix_equal('field',self.t.loc[ix_im,self.IDcol])
            if len(ixs_fieldcenter)==0:
                raise RuntimeError(f'field {self.t.loc[ix_im,"field"]} does not have any entries in the fieldcenters file!!!')
            # Make sure the collumns are decimal degrees and save the SkyCoords into __coord__ column
            fieldcenters.assert_radec_cols_decimal_degrees('RAdeg','DECdeg',coordcol='__coord__',indices=ixs_fieldcenter)

            #fieldcenters.write(indices=ixs_fieldcenter)
            
            
            # preliminarely set it to 'success'. This gets overwritten if the linking is not successful!
            linked_successcode=-1
            
            # Prepare the construction of the output filenames 
            (outdirbasename,linkbasename)=os.path.split(self.t.loc[ix_im,'outfilename'])
            relname = f'../mef/{linkbasename}'
            outdirbasename=re.sub('\/$','',outdirbasename)
            if re.search('\/mef$',outdirbasename) is None:
                raise RuntimeError(f'Somethings is wrong, {outdirbasename} should have \'mef\' subdir!')
            linkbasename = re.sub('\.fits\.fz$','',linkbasename)

             
            # Loop through each field center to calculate overlap to each detecter
            for ix_fieldcenter in ixs_fieldcenter:
                #if fieldcenters.t.loc[ix_fieldcenter,'ampl']!=2: continue
            
                #initialize
                detectoroffsets.t['RA_overlap_frac']=np.nan
                detectoroffsets.t['Dec_overlap_frac']=np.nan
            
                # only calculate overlap for the detectors that are within the max_separation_Dec of the Dec of fieldcenters 
                ixs_detectors =  detectoroffsets.ix_inrange('Dec_detector',fieldcenters.t.loc[ix_fieldcenter,'DECdeg']-max_separation_Dec,fieldcenters.t.loc[ix_fieldcenter,'DECdeg']+max_separation_Dec)  
                #ixs_detectors =  detectoroffsets.getindices()

                # we are in the small angle regime, therefore we can do this with cos term
                cosdec = np.cos(fieldcenters.t.loc[ix_fieldcenter,'__coord__'].dec.to('radian'))

                # calculate overlap to each detecter
                # overlap_deg = max_separation_Dec - abs(Dec(det)-Dec(fieldcenter)) is the overlap in deg
                # overlap_frac = overlap_deg/detector_boxsize is the fraction with respect to the detector boxsize
                # overlap_frac can be > 1.0 if the tile is bigger than the detector, thus set overlap_frac=1.0 if >1.0
                detectoroffsets.t.loc[ixs_detectors,'Dec_overlap_frac'] = np.minimum(1.0,(max_separation_Dec - np.abs(detectoroffsets.t.loc[ixs_detectors,'Dec_detector']-fieldcenters.t.loc[ix_fieldcenter,'DECdeg']))/self.detector_boxsize_Dec)
                # Note the cosdec term which scales down the difference between RA(det)-RA(fieldcenter)!
                detectoroffsets.t.loc[ixs_detectors,'RA_overlap_frac'] = np.minimum(1.0,(max_separation_RA - cosdec*np.abs(detectoroffsets.t.loc[ixs_detectors,'RA_detector']-fieldcenters.t.loc[ix_fieldcenter,'RAdeg']))/self.detector_boxsize_RA)
                detectoroffsets.t.loc[ixs_detectors,'Area_overlap_frac'] = detectoroffsets.t.loc[ixs_detectors,'RA_overlap_frac']*detectoroffsets.t.loc[ixs_detectors,'Dec_overlap_frac']
          
                if self.verbose>2:
                    print('detectors with some overlap:')
                #detectoroffsets.write()
                    detectoroffsets.write(indices=ixs_detectors)

                # Now make the cut: require a minimum Area overlap 
                ixs_final = detectoroffsets.ix_inrange('Area_overlap_frac',min_overlap_fraction,None,indices=ixs_detectors)
                if len(ixs_final)==0:
                    if self.verbose: print(f'WARNING: no detectors found matching for field={self.t.loc[ix_im,"field"]} tile={fieldcenters.t.loc[ix_fieldcenter,"ampl"]}')
                else:
                    if self.verbose>1:
                        print(f'field={fieldcenters.t.loc[ix_fieldcenter,"field"]} tile={fieldcenters.t.loc[ix_fieldcenter,"ampl"]}: {len(ixs_final)} detectors match!')
                    if self.verbose>2:
                        detectoroffsets.write(indices=ixs_final)
                        
                #substitute mef with the tilenumber (for historic reasons called 'ampl' in fieldcenters file)
                outdirname=re.sub('\/mef$',f'/{fieldcenters.t.loc[ix_fieldcenter,"ampl"]}',outdirbasename)
                if clobberlinks:
                    files=glob.glob(f'{outdirname}/{linkbasename}_*.fits.fz')
                    if len(files)>0:
                        if self.verbose>3: print('Removing these links:',files)
                        rmfiles(files)

                for ix_detector in ixs_final:
                    # This is the detector name, e.g. S30 etc
                    detname=detectoroffsets.t.loc[ix_detector,'detname']
                    linkname = f'{outdirname}/{linkbasename}_{detname}.fits.fz'
                    (successcode,successstr)=self.linkfiles(self.t.loc[ix_im,'outfilename'],relname,linkname, clobber=clobberlinks, deeplinkcheck=deeplinkcheck)
                    if successcode>linked_successcode:
                        self.t.loc[ix_im,'linked']=successstr
                        linked_successcode=successcode
        return(0)
    
    def set_tile_boxsizes(self, tilepattern=None, tile_boxsize_RA=None, tile_boxsize_Dec=None, tile_boxsize_padding_arcsec=None):
        #if tilepattern is None:
        if (tile_boxsize_RA is not None) and (tile_boxsize_Dec is not None):
            self.tile_boxsize_RA = float(tile_boxsize_RA)
            self.tile_boxsize_Dec = float(tile_boxsize_Dec)
        else:
            if tilepattern=='detector':
                if self.verbose>1: print('Setting tile boxsizes to detector box size!')
                self.tile_boxsize_RA = self.detector_boxsize_RA
                self.tile_boxsize_Dec = self.detector_boxsize_Dec
            # parse tilepattern of the form AxB, where A is Nra and B is Ndec
            elif re.search('^\d+x\d+$',tilepattern) is not None:
                m = re.search('(^\d+)x(\d+$)',tilepattern) 
                if m is None: raise RuntimeError('BUGGGGG!!!!!')
                Nra=int(m.groups()[0])
                Ndec=int(m.groups()[1])
                if self.verbose: print(f'Setting tile boxsizes to {Nra}x{Ndec} tilepattern, assuming DECam FOV diameter of {self.FOV_diameter_deg} degree!')
                self.tile_boxsize_RA = self.FOV_diameter_deg/Nra
                self.tile_boxsize_Dec = self.FOV_diameter_deg/Ndec
            else:
                raise RuntimeError(f'tilepattern {tilepattern} not known!')
            if self.verbose: print(f'tile_boxsize_RA={self.tile_boxsize_RA:.5f} tile_boxsize_Dec={self.tile_boxsize_Dec:.5f}')

        if self.tile_boxsize_RA is None or self.tile_boxsize_Dec is None:
            raise RuntimeError(f'tile_boxsize_RA and/or tile_boxsize_Dec cannot be None! ({self.tile_boxsize_RA},{self.tile_boxsize_Dec})') 

        # Add padding?
        if tile_boxsize_padding_arcsec is not None: 
            print(f'tile_boxsize_padding_arcsec={tile_boxsize_padding_arcsec:.0f} arcsec at EACH side: Adding {2*tile_boxsize_padding_arcsec:.0f} arcsec={2*tile_boxsize_padding_arcsec/3600.0:.5f} deg to each tile_boxsize!')
            self.tile_boxsize_RA+=2*tile_boxsize_padding_arcsec/3600.0
            self.tile_boxsize_Dec+=2*tile_boxsize_padding_arcsec/3600.0

        if self.verbose: print(f'tile_boxsize_RA={self.tile_boxsize_RA:.5} tile_boxsize_Dec={self.tile_boxsize_Dec:.5}')

    
    def calc_product_stats(self, ixs_pointings=None, ixs_im=None):

        # loop through all pointings
        ixs_pointings = self.pointingtable.getindices(indices=ixs_pointings)
        if len(ixs_pointings)==0:
            print('WARNING! NO POINTINGS??? BUG?')
            return(1)
        
        cols_counting = ['Nprod','dl_Nprod']
        
        for ix_pointing in ixs_pointings:
            # get all products for a given pointing
            ID = self.pointingtable.t.loc[ix_pointing,self.IDcol]
            ixs_im_ID = self.ix_equal(self.IDcol,ID,indices=ixs_im)
            self.pointingtable.t.loc[ix_pointing,'Nprod'] = len(ixs_im_ID)
            ixs_im_exist = self.ix_equal('dl_code',2,indices=ixs_im_ID)
            self.pointingtable.t.loc[ix_pointing,'dl_Nprod'] = len(ixs_im_exist)
        
            # loop through all possible proc_types, and count
            for proc_type in ['instcal','raw','resampled','skysub','stacked','mastercal','projected']:
                ixs_im_proc_type = self.ix_equal('proc_type',proc_type,indices=ixs_im_ID)
                if len(ixs_im_proc_type)>0:
                    noirsuffices = unique(self.t.loc[ixs_im_proc_type,'noirsuffix'])
                    noirsuffices.sort()
                    for noirsuffix in noirsuffices:
                        ixs_im_noirsuffices = self.ix_equal('noirsuffix',noirsuffix,indices=ixs_im_proc_type)
                        self.pointingtable.t.loc[ix_pointing,'N'+noirsuffix] = len(ixs_im_noirsuffices)
                        ixs_im_noirsuffices_exist = self.ix_equal('dl_code',2,indices=ixs_im_noirsuffices)
                        self.pointingtable.t.loc[ix_pointing,'dl_N'+noirsuffix] = len(ixs_im_noirsuffices_exist)
                        cols_counting.extend(['N'+noirsuffix,'dl_N'+noirsuffix])

            self.pointingtable.t.loc[ix_pointing,'complete'] = (len(ixs_im_ID) == len(ixs_im_exist))
            

        cols_counting = unique(cols_counting)
        for col in cols_counting: 
            self.pointingtable.t[col] = self.pointingtable.t[col].astype(pd.Int64Dtype())
    
        return(0)

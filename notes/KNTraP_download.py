#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun  7 19:27:04 2021

@author: arest
"""
import sys,os,argparse,re
from astropy.time import Time
import pandas as pd
from pandas.core.dtypes.common import is_object_dtype,is_float_dtype,is_integer_dtype


if 'PIPE_PYTHONSCRIPTS' in os.environ:
    sys.path.append(os.environ['PIPE_PYTHONSCRIPTS']+'/DECAMNOAO')
# make sure pdastro is in same dir if photpipe is not initialized!
from kntrap_decam_download import kntrap_decam_downloadclass,getlimits

class kntrap_downloadclass(kntrap_decam_downloadclass):
    def __init__(self):
        kntrap_decam_downloadclass.__init__(self)

    def add_arguments(self, parser=None, usage=None, conflict_handler='resolve'):
        (parser,group_photpipe) = kntrap_decam_downloadclass.add_arguments(self,parser=parser, usage=usage, conflict_handler=conflict_handler)

        # define the default fieldcenters and pointing file
        #default_fieldcentersfile=f'{os.environ["PIPE_CONFIGDIR"]}/{os.environ["PIPENAME"]}.fieldcenters'
        #default_pointingfile=f'{os.environ["PIPE_CONFIGDIR"]}/{os.environ["PIPENAME"]}.pointings.txt'


        #if 'PIPE_CONFIGDIR' in os.environ:
        #    default_kntrap_SN_list = '%s/kntrap_SN_pointings_decam.txt' % (os.environ['PIPE_CONFIGDIR'])
        #else:
        #    default_kntrap_SN_list = None
           
        parser.add_argument('--pointing2im_columns', nargs="+", default=['pointing','group'], help='specify list of columns to be copied from the pointing table to the image table (default=%(default)s)')
#        parser.add_argument('--outfieldcol', default="SNID", help='output field column name of input list (default=%(default)s)')
#        parser.add_argument('--propID', nargs="+", default=['2021A-0275'], help='specify proposal IDs (default=%(default)s)')
#        parser.add_argument('-l', '--lookbacktime', type=float, default=10, help='lookback time in days.')
        parser.add_argument('--photpipe_outfilename', action='store_true', default=True, help='Make the subdir structure photpipe compatible (subdir is fieldname/1, and 2-62 subdirs are linked to 1. Give filenames in the form field.YYMMDD.filter_ID. (default=%(default)s)')

        # add a few more options to select certain entries
        parser.add_argument('--group_select', nargs="+", default=None, help='Select the group or group range. This will be applied to the group column of the pointing table. If single value, then exact match. If single value has "+" or "-" at the end, then it is a lower and upper limit, respectively. Examples: 440+, 440-, 440 480  (default=%(default)s)')
        parser.add_argument('--pointing_select', nargs="+", default=None, help='Select the pointing or pointing range. This will be applied to the ppinting column of the pointing. If single value, then exact match. If single value has "+" or "-" at the end, then it is a lower and upper limit, respectively. Examples: 403.D.a+, 403.D.a-, 403.D.a 403.F.a  (default=%(default)s)')
        parser.add_argument('--groups', nargs='+', default=None, type=int, help='Specify groups to download')
        parser.add_argument('--pointings', nargs='+', default=None, help='Specify pointings to download')

        group_photpipe.add_argument('--tilepattern', default='detector', 
                                    help='The tilepattern is used to determine the tile boxsizes. For KNTraP the tiles are just the detectors, so the tilesize is set to the default=%(default)s')
        group_photpipe.add_argument('--tile_boxsize_padding_arcsec', type=float, default=50, help='You can add extra padding to EACH side of the tiles,i.e. both tile_boxsize_* increase by 2xtile_boxsize_padding_arcsec (default=%(default)s)')

        return(parser,group_photpipe)
    
    def load_pointingtable(self,pointingfilename,**kwargs):
        errorflag = kntrap_decam_downloadclass.load_pointingtable(self,pointingfilename,**kwargs)
        # if 'group' is object, needs to be converted into float before Int64Dtype. No idea why!
        if is_object_dtype(self.pointingtable.t['group']):
            self.pointingtable.t['group']= self.pointingtable.t['group'].astype('float')
        self.pointingtable.t['group']= self.pointingtable.t['group'].astype(pd.Int64Dtype())
        return(errorflag)

if __name__ == "__main__":
    kntrap_download = kntrap_downloadclass()
    (parser,group_photpipe) = kntrap_download.add_arguments()
    args = parser.parse_args()
    
    kntrap_download.verbose=args.verbose
    kntrap_download.debug=args.debug
    
    # eventpipe overrides photpipe
    if args.eventpipe_outfilename: args.photpipe_outfilename=False
    
    # login and token
    if args.login is not None:
        kntrap_download.NOIRlogin(args.login[0],args.login[1])
    if args.token is not None:
        kntrap_download.token=args.token

    # make sure kntrap_download.IDcol is set 
    kntrap_download.setIDcol(args.IDcol)
    # make sure kntrap_download.tile_boxsize_RA and kntrap_download.tile_boxsize_Dec are set 
    kntrap_download.set_tile_boxsizes(tilepattern=args.tilepattern, 
                                   tile_boxsize_RA=args.tile_boxsize_RA, 
                                   tile_boxsize_Dec=args.tile_boxsize_Dec, 
                                   tile_boxsize_padding_arcsec=args.tile_boxsize_padding_arcsec)

    # download the pointing table
    kntrap_download.load_pointingtable(args.pointingfile,racol=args.racol,deccol=args.deccol)
    
    # select on ranges in pointing file
    ixs_pointings = kntrap_download.pointingtable_selectrange('group',args.group_select)
    ixs_pointings = kntrap_download.pointingtable_selectrange('pointing',args.pointing_select,indices=ixs_pointings)
    ixs_pointings = kntrap_download.pointingtable_selectrange(kntrap_download.IDcol,args.ID_select,indices=ixs_pointings)

    # select on lists in pointing file
    ixs_pointings = kntrap_download.pointingtable_selectlist('group',args.groups,indices=ixs_pointings)
    ixs_pointings = kntrap_download.pointingtable_selectlist('pointing',args.pointings,indices=ixs_pointings)
    ixs_pointings = kntrap_download.pointingtable_selectlist(kntrap_download.IDcol,args.IDs,indices=ixs_pointings)
    
    
    ixs_pointings = kntrap_download.pointingtable.ix_sort_by_cols(kntrap_download.IDcol,indices=ixs_pointings)
    print(f'{len(ixs_pointings)} entries selected in pointing file')
    kntrap_download.pointingtable.write(indices=ixs_pointings)

    # for each pointing, find all the images
    kntrap_download.find_images_all_pointings(indices=ixs_pointings,
                                            searchradius=args.searchradius,
                                            imagequalityflag=args.image_quality,
                                            pointing2im_columns=args.pointing2im_columns,
                                            aux_columns_archive=args.aux_columns,
                                            lookbacktime=args.lookbacktime,
                                            proc_type=args.proc_type,
                                            prod_type=args.prod_type,
                                            obs_type=args.obs_type,
                                            propID=args.propID,
                                            imoutcols=args.imoutcols)
    
    if len(kntrap_download.t)<1:
        print('NO PRODUCTS! exiting...')
        sys.exit(0)

    # cut down the product list
    ixs_im_keep = kntrap_download.date_select(args.date_select)
    ixs_im_keep = kntrap_download.expnum_select(args.expnum_select,indices=ixs_im_keep)
    ixs_im_keep = kntrap_download.expnum_list(args.expnum_list,indices=ixs_im_keep)
    ixs_im_keep = kntrap_download.filter_select(args.filters,indices=ixs_im_keep)
    
    # remove double entries for images that have more than one version
    if args.proc_type[0] == 'stacked':
        print('Warning: check4doubleentries not performed.')
    else:
        print('*********%%%%%%%%',args.proc_type)
        ixs_im_keep = kntrap_download.check4doubleentries(indices=ixs_im_keep)
    
    # get the output filenames
    kntrap_download.mk_outfilenames(indices=ixs_im_keep,
                                 outrootdir=args.outrootdir, 
                                 photpipe_outfilename=args.photpipe_outfilename or args.photpipe_old_outfilename, 
                                 eventpipe_outfilename=args.eventpipe_outfilename,
                                 tmpl = args.tmpl,
                                 ID2outsubdir=args.ID2outsubdir, 
                                 info2filename=args.info2filename,
                                 skip_check_if_outfile_exists=args.skip_check_if_outfile_exists
                                 )
    
    # calculate the statistics hpw many products have been already downloaded
    kntrap_download.calc_product_stats(ixs_pointings=ixs_pointings, ixs_im=ixs_im_keep)   
    
    # Show the list of all selected products  
    print('\n### product list for all pointings:')
    kntrap_download.write(columns=kntrap_download.imoutcols,indices=ixs_im_keep)

    # Show the list and statistics of all selected pointinngs  
    print('\n### Summary pointings:')
    kntrap_download.pointingtable.write(indices=ixs_pointings)

    # download the products
    (errflag,ixs_downloaded) = kntrap_download.download_products(indices=ixs_im_keep, clobber=args.clobber, skip_confirm_download=args.skip_confirm_download)
    # stop if nothing downloaded, and not deeplinkcheck or clobber
    if len(ixs_downloaded)==0 and (not args.deeplinkcheck) and (not args.clobberlinks):
        print('Nothing new got downloaded, skipping checking the photpipe links, exiting...')
        sys.exit(0)
        

    # Make links if wanted!
    if args.photpipe_outfilename:
        kntrap_download.make_and_check_photpipe_links(indices=ixs_im_keep, 
                                                   min_overlap_fraction=args.min_overlap_fraction,
                                                   fieldcenter_file=args.fieldcenter_file,
                                                   clobberlinks=args.clobberlinks, 
                                                   deeplinkcheck=args.deeplinkcheck)
    elif args.photpipe_old_outfilename:
        kntrap_download.make_and_check_photpipe_links(indices=ixs_im_keep, 
                                                   clobber=args.clobber, 
                                                   deeplinkcheck=args.deeplinkcheck)
    elif args.eventpipe_outfilename:
        raise RuntimeError('eventpipe_outfilename not yet implemented!')

    print('\n### Image list with download results')
    kntrap_download.write(columns=kntrap_download.imoutcols,indices=ixs_im_keep)

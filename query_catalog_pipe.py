# iuery catalogs for photometric (and astrometry) calibration
__author__ = "Igor Andreoni"

import os

import numpy as np
from astropy.io import ascii
from astropy.coordinates import SkyCoord
import astropy.units as u
from astroquery.vizier import Vizier


class PhotoCatalog:
    """
    A class to provide a catalog for photometric calibration.

    Standard usage:
     cat = PhotoCatalog((ra, dec), field_size, catname)  # with ra, dec 
           in degrees and field_size is the side of the field in arcmin
     t_cat = cat.query()
    """
    def __init__(self, field_center, field_size, catname, fil='all'):
        """Runs when the class is invoked
        Parameters
        ----------
        field_center tuple of floats
            (ra, dec) in degrees
        field_size float
            search box side in arcmin
        catname str
            catalog name
        fil str
            selected filter (or 'all' to get them all)
        """
        self.field_ra = field_center[0]
        self.field_dec = field_center[1]
        self.boxsize = field_size * u.arcmin
        self.catalog = catname
        self.filter = fil
        # Catalog: Gaia DR2
        if "gaia" in catname or "Gaia" in catname:
            self.catID = "I/345/gaia2"
        # Catalog: Pan-STARRS DR1
        elif "ps1" in catname or "PS1" in catname or "Pan" in catname:
            self.catID = "II/349/ps1"
        # Catalog: APASS DR9
        elif "apass" in catname or "APASS" in catname:
            self.catID = "II/336/apass9"
        # Catalog: SkyMapper DR1
        elif "skymapper" in catname or "SM" in catname or "SkyMapper" in catname:
            self.catID = "II/358/smss"
        else:
            print("Catalog name not recognized! Available catalogs:")
            print("Gaia, APASS, PS1")
            return None

    def query(self):
        """
        Query Vizier server for sources found in a box with center
        self.field_ra, self.field_dec (in deg) and width
        self.field_width (in arcmin).
        Returns a table (if objects found) or None (if not)
        """
        # Create a SkyCoord object
        coords = SkyCoord(ra=self.field_ra*u.deg,
                          dec=self.field_dec*u.deg)
        # Select only those columns with relevant info
        if self.catID == "I/345/gaia2":
            columns_select = ['Source', 'RA_ICRS', 'e_RA_ICRS',
                              'DE_ICRS', 'e_DE_ICRS', 'Gmag', 'e_Gmag']

        elif self.catID == "II/349/ps1":
            columns_select = ['objID', 'RAJ2000', 'DEJ2000']
            if self.filter == 'all':
                columns_select += ["gmag", "e_gmag",
                                   "rmag", "e_rmag",
                                   "imag", "e_imag",
                                   "zmag", "e_zmag",
                                   "ymag", "e_ymag"
                                    ]
            else:
                columns_select += [f"{self.filter}mag",
                                   f"e_{self.filter}mag"]

        elif self.catID == "II/358/smss":
            columns_select = ['ObjectId', 'RAICRS', 'DEICRS']
            if self.filter == 'all':
                columns_select += ['uPSF', 'e_uPSF',
                                   'vPSF', 'e_vPSF',
                                   'gPSF', 'e_gPSF',
                                   'rPSF', 'e_rPSF',
                                   'iPSF', 'e_iPSF',
                                   'zPSF', 'e_zPSF'
                                   ]
            else:
                columns_select += [f"{self.filter}PSF",
                                   f"e_{self.filter}PSF"]

        elif self.catID == "II/336/apass9":
            columns_select = ['RAJ2000', 'DEJ2000']
            if self.filter == 'all':
                columns_select += ['Vmag', 'e_Vmag',
                                   'Bmag', 'e_Bmag',
                                   "g'mag", "e_g'mag",
                                   "r'mag", "e_r'mag",
                                   "i'mag", "e_i'mag"
                                   ]
            else:
                columns_select += [f"{self.filter}mag",
                                   f"e_{self.filter}mag"]
        # Vizier object
        v = Vizier(columns=columns_select, row_limit=-1)
        # Query Vizier
        t_result = v.query_region(coords, width=self.boxsize,
                                height=self.boxsize,
                                catalog=self.catID)
        # Check if the sources were found
        if len(t_result) == 0:
            return None
        else:
            return t_result[self.catID]


class GaiaAstrometry:
    """
    A class to provide a Gaia catalog for astrometric calibration.
    The init function produces, for any requested field,
    a catalog of sources from Gaia DR2

    Standard usage:
     gaia = GaiaAstrometry( (ra, dec), field_size )  # with ra, dec 
                in degrees and field_size is the side of the field in arcmin
     t_gaia = gaia.query_gaia_astrom()

    To use SCamp, the table needs to be saved in FITS LDAC format. Here
    is a very useful code to do that:
    https://astromatic-wrapper.readthedocs.io/en/latest/_modules/astromatic_wrapper/utils/ldac.html
    """
    def __init__(self, field_center, field_size):
        self.field_ra = field_center[0]
        self.field_dec = field_center[1]
        self.boxsize = field_size * u.arcmin
        # Catalog: Gaia DR2
        self.catID = "I/345/gaia2"

    def query_gaia_astrom(self):
        """
        Query Vizier server for Gaia sources found in a box with center
        self.field_ra, self.field_dec (in deg) and width
        self.field_width (in arcsec).
        Returns a table (if objects found) or None (if not)
        """
        # Create a SkyCoord object
        coords = SkyCoord(ra=self.field_ra*u.deg,
                          dec=self.field_dec*u.deg)
        # Select only those columns with relevant info for Scamp
        columns_select = ['RA_ICRS', 'e_RA_ICRS', 'DE_ICRS', 'e_DE_ICRS',
                          'Source', 'Gmag', 'e_Gmag']
        # Vizier object
        v = Vizier(columns=columns_select, row_limit=-1)
        # Query Vizier
        t_result = v.query_region(coords, width=self.boxsize,
                                height=self.boxsize,
                                catalog=self.catID)
        # Check if the sources were found
        if len(t_result[self.catID]) == 0:
            return None
        else:
            return t_result[self.catID]


def write_file(t, pathdir, fieldname, filt, ccd, catname):
    """Write the catalog in a format that photpipe likes

    Parameters
    ----------
    t astropy table
        Table with the query results
    pathdir str
        Path to the destination directory
    fieldname str
        Name of the field observed
    fil str
        Filter
    ccd int or str
        CCD number
    catname str
        Name of the catalog that was queried

    """
    #The output must be like: <fieldname>_<filter>_<CCD#>_<catname>_phot.cat
    outfile = f"{pathdir}/{fieldname}_{filt}_{ccd}_{catname}_phot.cat"
    with open(outfile, "w") as f:
        # Take only the first letter of the filters for the header
        f.write(f"#         ra         dec       {filt[0]}      d{filt[0]}\n")
        for l in t:
            f.write(f"{l['ra']} {l['dec']} {l['mag']} {l['e_mag']}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Query photometric catalogs')

    parser.add_argument('-f', '--filename', dest='filename',
                        type=str, help='File with field centers per ccd',
                        default='KNTraP.fieldcenters')
    parser.add_argument('-c', '--catalog',
                        dest='catname', type=str,
                        default='SM',
                        help='Catalog to be queried (SM, PS1, APASS, Gaia)')
    parser.add_argument('-o', '--out-path',
                        dest='pathdir', type=str,
                        default='catalogs_photometry',
                        help='Path to the directory where the files will \
be saved')
    parser.add_argument('-s', '--field-size',
                        dest='field_size', type=float,
                        default=18,
                        help='Side of the catalog search box (arcmin)')
    parser.add_argument('-b', '--bright',
                        dest='bright_thresh', type=float,
                        default=5,
                        help='Brightness (mag) threshold for stars to be flagged')
    parser.add_argument('--clobber',
                        dest='clobber', action='store_true', default=False,
                        help='Clobber (default False)')
    parser.add_argument('-v', '--verbose',
                        dest='verbose', action='store_true', default=False,
                        help='Prints out how many sources were found per field')
    args = parser.parse_args()

    # Read the file with fields info
    t_centers = ascii.read(args.filename[0])
    # One query for each pointing
    for c in t_centers:
        # Iterate over filters
        ra = c['RAdeg']
        dec = c['DECdeg']
        for fil in ['g', 'i']:
            if args.catname == 'APASS':
                fil = fil + "'"
            # Is the file already existent?
            if args.clobber is False:
                outfile = f"{args.pathdir}/{c['field']}_{fil[0]}_{c['ampl']}_{args.catname}_phot.cat"
                if os.path.isfile(outfile):
                    continue
            cat = PhotoCatalog((ra, dec), args.field_size, args.catname, fil=fil) 
            t_cat = cat.query()
            if t_cat is None:
                print(f"Watch out! No {args.catname} for field {c['field']}, \
CCD {c['ampl']}? Trying again...")
                t_cat = cat.query()
                if t_cat is None:
                    print(f"...No hope, sorry.")
                    continue
            # Make the table column names standard
            if args.catname == 'APASS' or 'ps1' in args.catname or 'PS1' in args.catname or 'Pan' in args.catname:
                t_cat.rename_column("RAJ2000", "ra")
                t_cat.rename_column("DEJ2000", "dec")
                t_cat.rename_column(f"{fil[0]}_mag", "mag")
                t_cat.rename_column(f"e_{fil[0]}_mag", "e_mag")
            if "SM" in args.catname or "skymapper" in args.catname or "SkyMapper" in args.catname:
                t_cat.rename_column("RAICRS", "ra")
                t_cat.rename_column("DEICRS", "dec")
                t_cat.rename_column(f"{fil}PSF", "mag")
                t_cat.rename_column(f"e_{fil}PSF", "e_mag")
            # Select only non-masked values
            t_cat["mag"].fill_value = 99
            # Find bright stars
            mags = np.array(t_cat['mag'])
            # ..and remove NaNs
            nan_index = [i for i in np.arange(len(mags)) if np.isnan(mags[i])]
            mags = np.delete(mags, nan_index)
            t_cat.remove_rows(nan_index)
            if np.size(np.where(mags < args.bright_thresh)[0]) > 0:
                t_bright = t_cat[t_cat['mag'] < args.bright_thresh]
                print(f"Careful! Bright objects mag < {args.bright_thresh} \
near field {c['field']}, filter {fil[0]}, ccd {c['ampl']}")
                print(t_bright)
            # Select only reasonable mags
            t_cat = t_cat[(t_cat['mag'] < 30)]
            write_file(t_cat, args.pathdir, c['field'], fil[0], c['ampl'],
                       args.catname)
            if args.verbose is True:
                print(f"Found {len(t_cat)} sources for field {c['field']}, \
filter {fil[0]}, ccd {c['ampl']}")

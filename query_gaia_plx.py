# Author: Igor Andreoni

from query_catalog_pipe import GaiaAstrometry
from astropy.coordinates import SkyCoord
import astropy.units as u 


def query_coords_gaia(ra, dec, radius_arcsec=2.):
    gaia = GaiaAstrometry((ra, dec), radius_arcsec/60)
    t_gaia = gaia.query_gaia_astrom()
    coords = SkyCoord(t_gaia['RA_ICRS'], t_gaia['DE_ICRS'])
    sep = coords.separation(SkyCoord(ra*u.deg, dec*u.deg))
    t_gaia["separation"] = sep.to('arcsec')
    print(t_gaia)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Gaia parallax')
    parser.add_argument('radec', metavar='RA, Dec', type=str, nargs='+',
                        help='RA and Dec (degrees)')
    parser.add_argument('-r', dest='radius', type=float,
                        required=False, help='Search radius (arcsc)',
                        default=2)
    args = parser.parse_args()

    # RA and Dec
    ra, dec = float(args.radec[0]), float(args.radec[1])

    # Radius
    search_rad = args.radius
    query_coords_gaia(ra, dec, radius_arcsec=search_rad)

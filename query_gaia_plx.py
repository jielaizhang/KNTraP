# Author: Igor Andreoni

from query_catalog_pipe import GaiaAstrometry



def query_coords_gaia(ra, dec, radius_arcsec=2.):
    gaia = GaiaAstrometry((ra, dec), radius_arcsec/60)
    t_gaia = gaia.query_gaia_astrom()
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

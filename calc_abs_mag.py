from astropy.cosmology import Planck15 as cosmo
import astropy.units as u
import numpy as np
import argparse
import matplotlib.pyplot as plt


# Function to get Mpc x-axis
def tick_function(redshift):
    D = cosmo.luminosity_distance(redshift).value
    return ["%.1f" % x for x in D]

# Get Arguments
parser = argparse.ArgumentParser(description='Make Absolute Mag versus redshift plot.')
parser.add_argument('apparent_mag', metavar='m', type=float,
                    help='Put in the apparent magnitude')
parser.add_argument('redshift_range',type=str, help='put lower (z from 0.001 to 0.1) or higher (z from 0.01 to 1.0)')
parser.add_argument('specifiz_z',type=float,help='put a specifc z you want a print out for')
args   = parser.parse_args()


# convert m to flux density energy/s/area/Hz 1 Jy = (1/10^23) erg/cm2/s/Hz
fluxdensity_Jy = 10**(args.apparent_mag/-2.5) * 3631

# To print specific something
z_one = args.specifiz_z
M_one = args.apparent_mag - cosmo.distmod(z_one).value
D_L_one_Mpc = cosmo.luminosity_distance(z_one).value
R_L_cm_one = D_L_one_Mpc* 3.086e22 * 100
area_one = 4*np.pi*R_L_cm_one**2
specifc_Lum_one = fluxdensity_Jy * area_one
print(f'for m={20}, z={z_one}, M={M_one:0.3f}, 10^23*erg/s/Hz={specifc_Lum_one:0.3e}, D_L={D_L_one_Mpc:0.2f} Mpc')

###############################################
######## Calculate M, D_L, Luminosity #########
if args.redshift_range == 'lower':
    z   = np.linspace(0.001,0.1,100)
    tick_locations = np.linspace(0.001,0.1,8)
elif args.redshift_range == 'higher':
    z   = np.linspace(0.01,1.0,100)
    tick_locations = np.linspace(0.01,1.0,8)
M       = args.apparent_mag - cosmo.distmod(z).value
D_L_Mpc = cosmo.luminosity_distance(z).value

# convert flux to erg/s/Hz with luminosity distance
R_L_cm = D_L_Mpc * 3.086e22 * 100
area   = 4*np.pi*R_L_cm**2
specific_luminosity = fluxdensity_Jy * area
###############################################

###############################################
# Plot with grid lines for M
fig, ax1 = plt.subplots()
ax1.set_title(f'for m={args.apparent_mag}')
ax2 = ax1.twinx()

ax1.plot(z,M, 'g-')
ax1.set_ylabel('Absolute Mag',color='g')
ax1.set_xlabel('redshift, z')
ax1.minorticks_on()
ax1.grid(b=True, which='major', color='g', linestyle='-',alpha=0.2)
ax1.grid(b=True, which='minor', color='g', linestyle='--', alpha=0.1)

ax2.plot(z,specific_luminosity,'b-')
ax2.set_ylabel('ergs/s/Hz',color='b')
ax2.minorticks_on()

ax3 = ax1.twiny()
ax3.set_xlim(ax1.get_xlim())
ax3.set_xticks(tick_locations)
ax3.set_xticklabels(tick_function(tick_locations))
ax3.set_xlabel(r"Luminosity Dist (Mpc)")

plt.savefig(f'z_versusM_{args.redshift_range}_m{args.apparent_mag}.png',bbox_inches='tight')
###############################################

###############################################
# Plot with grid lines for erg/s/Hz
fig, ax1 = plt.subplots()
ax1.set_title(f'for m={args.apparent_mag}')
ax2 = ax1.twinx()

ax2.plot(z,specific_luminosity, 'b-')
ax2.set_ylabel('ergs/s/Hz',color='b')
ax2.set_xlabel('redshift, z')
ax2.minorticks_on()
ax1.xaxis.grid(True,which='major',color='b', linestyle='-',alpha=0.2)
ax2.grid(b=True, which='major', color='b', linestyle='-',alpha=0.2)
ax2.grid(b=True, which='minor', color='b', linestyle='--', alpha=0.1)

ax1.plot(z,M,'g-')
ax1.set_ylabel('Absolute Mag',color='g')
ax1.minorticks_on()

ax3 = ax1.twiny()
ax3.set_xlim(ax1.get_xlim())
ax3.set_xticks(tick_locations)
ax3.set_xticklabels(tick_function(tick_locations))
ax3.set_xlabel(r"Luminosity Dist (Mpc)")

plt.savefig(f'z_versusE_{args.redshift_range}_m{args.apparent_mag}.png',bbox_inches='tight')
###############################################

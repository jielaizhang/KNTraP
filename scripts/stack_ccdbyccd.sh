for ext in {1..61}
do
      echo ###################
      echo --------
      echo "swarp CPinstcal_GRB210605A5*_20210607*_g_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210607/GRB210605A5_20210607_g_stack_ext$ext.fits"
      swarp CPinstcal_GRB210605A5*_20210607*_g_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210607/GRB210605A5_20210607_g_stack_ext$ext.fits
      echo --------
      echo "swarp CPinstcal_GRB210605A5*_20210607*_i_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210607/GRB210605A5_20210607_i_stack_ext$ext.fits"
      swarp CPinstcal_GRB210605A5*_20210607*_i_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210607/GRB210605A5_20210607_i_stack_ext$ext.fits
      echo --------
      echo "swarp CPinstcal_GRB210605A5*_20210608*_g_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210608/GRB210605A5_20210608_g_stack_ext$ext.fits"
      swarp CPinstcal_GRB210605A5*_20210608*_g_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210608/GRB210605A5_20210608_g_stack_ext$ext.fits
      echo --------
      echo "swarp CPinstcal_GRB210605A5*_20210608*_i_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210608/GRB210605A5_20210608_i_stack_ext$ext.fits"
      swarp CPinstcal_GRB210605A5*_20210608*_i_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210608/GRB210605A5_20210608_i_stack_ext$ext.fits
      echo --------
      echo "swarp CPinstcal_GRB210605A5*_20210609*_g_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210609/GRB210605A5_20210609_g_stack_ext$ext.fits"
      swarp CPinstcal_GRB210605A5*_20210609*_g_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210609/GRB210605A5_20210609_g_stack_ext$ext.fits
      echo --------
      echo "swarp CPinstcal_GRB210605A5*_20210609*_i_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210609/GRB210605A5_20210609_i_stack_ext$ext.fits"
      swarp CPinstcal_GRB210605A5*_20210609*_i_*/*ext$ext.fits* -IMAGEOUT_NAME GRB210605A5_20210609/GRB210605A5_20210609_i_stack_ext$ext.fits
done

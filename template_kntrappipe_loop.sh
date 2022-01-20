for fieldname in GRB210605A5 GRB210605A4
do
    for caldate in 20210607 20210608
    do
        for band in g
        do
            for ext in {31..33}
            do
                echo #############
                echo -------------
                echo python submit_slurm_ozstar.py -v $fieldname $caldate $band $ext
                python submit_slurm_ozstar.py -v $fieldname $caldate $band $ext
            done # ext
        done # band
    done #caldate
done #fieldname


#!/usr/bin/env perl

push(@INC, $ENV{"PIPE_PERL"});
require "genericprocs.pl";
require Modules::Statistics::Descriptive;
use POSIX qw(log10 floor ceil);

$FLAG_BONAFIDE_MATCH       = 0x10000;
$FLAG_GOOD_AMBIGUOUS_MATCH = 0x20000;
$FLAG_BAD_AMBIGUOUS_MATCH  = 0x80000;

my $MAG_AT_UNCERTAINTY_FLAG = 0;
my $MAU_BINSIZE = 0.05;
my $MAU_NITERMAX = 8;
my $MAU_NSIG = 3.0;
my $MAU_NMIN4BIN = 10;
my $MAU_MAXSTDEVRATIO = 2.0;
my @MAU_TYPES = (0x1);
my $MAU_STATSTYPE = "median";
my @MAU_DMAGLIST = (0.01,0.015,0.02,0.05,0.1);
my $MAU_SAVELIST = 0;

if ($#ARGV < 1){
    printf STDERR "Usage: absphot.pl cmpfile matchlist [-r radius][-outfile outfilename][-type dophottypelist][-saveabsphotinfo]".
	"[-maxit maximumiteration][-sys_err error][-Nsigma Nsigma][-nooutputfiles]".
	"[-magaterr [<dMaglist>]][-magaterr_binsize <binsize>][-magaterr_Nmin4bin Nmin4bin][-magaterr_types typelist][-magaterr_savelist]\n";
    printf STDERR "-r radius: search radius for match in pixel\n";
    printf STDERR "-maxdM: only use cmp detections with dM<maxdM. \n";
    printf STDERR "-type: only use dophot types listed (separator: ',') \n";
    printf STDERR "-sys_err error: add a systematic error to the magnitudes in domagstats\n";
    printf STDERR "-nooutputfiles: No files are saved (if only mag difference is of interest)\n";
    printf STDERR "-magaterr: Calculates the magnitude for which the median uncertainty is a certain value, ".
	"where the uncertainties can be specified with <dMaglist>, or they are the default of ".join(",",@MAU_DMAGLIST).
	". The magnitudes are written to the header as MAU*\n";
    printf STDERR "-magaterr_binsize: magnitude binsize for -magaterr\n";
    printf STDERR "-magaterr_Nmin4bin: Minimum number of measurements in a magnitude bin required\n";
    printf STDERR "-magaterr_types: dophot types used, typelist is comma-separated\n";
    printf STDERR "-magaterr_savelist: saves the M to dM relation into cmpfile.M2dM\n";
    printf STDERR "-saveabsphotinfo: saves an extra file with a table of the M's and deltaM's of both the cmp and cat\n";
    printf STDERR "\n";

    exit(0);
}

$cmpfile = $ARGV[0];
$catfilename = $ARGV[1];
$outfile="";
$searchrad = 2;   ### thresh in pixels to associate objects
$dophottypelist="1";
$usedophottypelist="1";
$magstats=0;
$maxit=10;
$sys_err=0.0;
$Nsigma=3.0;
$savefiles=1;
$maxdM=0.0;

$DEBUG=0;

my $i = 2;
do {
    $i_save=$i;
    if ($ARGV[$i] eq "-outfile")       {$outfile=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-r")             {$searchrad=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-debug")         {$DEBUG=1;$i++;}
    if ($ARGV[$i] eq "-maxdM")         {$maxdM=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-type")          {$dophottypelist=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-usetype")       {$usedophottypelist=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-maxit")         {$maxit=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-sys_err")       {$sys_err=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-Nsigma")        {$Nsigma=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-nooutputfiles") {$savefiles=0;$i++;}
    if ($ARGV[$i] eq "-saveabsphotinfo"){$saveabsphotinfo=1;$i++;}
    if ($ARGV[$i] eq "-magaterr")      {$MAG_AT_UNCERTAINTY_FLAG = 1;$i++;
					if (($ARGV[$i] !~ /^\-/) && ($ARGV[$i] ne "")){
					    @MAU_DMAGLIST=split(/,/,$ARGV[$i++]);
					}}
    if ($ARGV[$i] eq "-magaterr_binsize") {$MAU_BINSIZE=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-magaterr_savelist"){$MAU_SAVELIST=1;$i++;}
    if ($ARGV[$i] eq "-magaterr_Nmin4bin"){$MAU_NMIN4BIN=$ARGV[++$i];$i++;}
    if ($ARGV[$i] eq "-magaterr_types")   {
	@MAU_TYPES=split(/,/,$ARGV[++$i]);$i++;
	for (my $j=0;$j<@MAU_TYPES;$j++) {
	    $MAU_TYPES[$j]=hex($MAU_TYPES[$j]) if ($MAU_TYPES[$j]=~/0x(\S+)/);
	}
    }
    if (($i_save==$i) && ($ARGV[$i] ne "")) {
	printf(STDERR "ERROR absphot.pl: wrong flag: <$ARGV[$i]>, exiting...\n");exit(0);
    }
} while ($i < @ARGV);

die "couldn't open $cmpfile!" if (!(-e $cmpfile));
die "couldn't open $catfilename!" if (!(-e $catfilename));

@dophottypes=split(/,/,$dophottypelist);
$check4dophottypeflag=(scalar(@dophottypes)>0);
@usedophottypes=split(/,/,$usedophottypelist);

### read in  matchfile and parse for x,y pairs

my @matchlist;
@matchlist = &cat2xy($catfilename,$cmpfile);
chomp(@matchlist);
@matchlist=sort xsort(@matchlist);
undef my @x2match; undef my @y2match; undef my @mag2match; undef my @dmag2match;
foreach $line (@matchlist){
    $line =~ s/^\s+//;
    my ($x,$y,$ra,$dec,@maginfo) = split(/\s+/,$line);
    push(@x2match,$x);
    push(@y2match,$y);
    push(@mag2match,$maginfo[0]);
    push(@dmag2match,$maginfo[1]);
}

die "ERROR: no stars in matchlist!\n" if (@matchlist<1);

### open cmpfile, get x's and y's
undef my @cmpdata;undef my @x_cmp;undef my @y_cmp;undef my @mag_cmp;undef my @dmag_cmp;undef my @type_cmp; undef my @mask_cmp;
my ($cmpheader,@cmpdata) = &LoadFromFile("$cmpfile");
chomp(@cmpdata);
@cmpdata=sort xsort(@cmpdata);
my $prefactor = 2.5/log(10.0);
#print STDERR "XXXX $prefactor\n";exit(0);
foreach (@cmpdata){
    my $line =$_;
    $line =~ s/^\s+//;
    my ($x,$y,$mag,$dmag,$flux,$dflux,$type,@cmpinfo) = split(/\s+/,$line);
    $type=hex($type) if ($type=~/0x(\S+)/);
    $type &= 0xf;
    push(@type_cmp,$type);
    push(@x_cmp,$x);
    push(@y_cmp,$y);
    push(@mask_cmp,@cmpinfo[13]);
    if ($type == 0x2){
	$dflux = 0.1*$flux;
	$dmag = $prefactor*$dflux/$flux;
    }

    if ($flux > 0.0){
	push(@mag_cmp,-2.5*log10($flux));
	push(@dmag_cmp,$prefactor * $dflux/$flux);
    } else {
	push(@mag_cmp,$mag);
	push(@dmag_cmp,$dmag);
    }
#    if ($type == 7){
}
#exit(0);

# get image dimensions
my ($errorflag,$NX,$NY)= &GetFitsKeywords($cmpfile,"NAXIS1","NAXIS2");
die ("ERROR: could not read NAXIS1 or NAXIS2 from fits header of file $cmpfile!\n") if ($errorflag);

# create pointers to the sorted lists: makes matching faster...
undef my @cmpindex;
@cmpindex=pointer2sortedlist($NX,@x_cmp);

#foreach (@x_cmp){
#    print STDERR "X: $_\n";
#}
#
#for($x=0;$x<=$NX;$x++){
#    print STDERR sprintf ("%4d: index:%4d  xcmp:%8.2f\n",$x,$cmpindex[$x],$x_cmp[$cmpindex[$x]]);
#}

$searchrad2=$searchrad*$searchrad;

undef my %Ntypehash;
foreach $dophottype (@dophottypes){
    $Ntypehash{$dophottype}=0;
}

undef my %cmp2catindex;

### go through marked objects and find em in cmp file
undef my @mags1;undef my @dmags1;undef my @mags2;undef my @dmags2;undef my @mags2compare;
undef my @matcheddata;undef my @nomatch;undef my @ambiguousmatch;
$Ngood=0;$Nbad=0;$Nambiguous=0;$Ntot=0;$Ndifferenttype=0;
for(my $i=0; $i<@x2match; $i++){
    my $xm = $x2match[$i];
    my $ym = $y2match[$i];

    # skip if x,y position of catalogue star is outside image
    next if (($xm<0-$searchrad) || ($xm>=$NX+$searchrad) || ($ym<0-$searchrad) || ($ym>$NY+$searchrad));
    $Ntot++;

    my $Ncmpfound=0;
    my $bestcmpdistance2=$searchrad2;my $bestcmpindex=-1;

    my $startx = int($xm-$searchrad);
    $startx = 0 if ($startx < 0);
    $startx = $NX if ($startx > $NX);
    my $jmin=$cmpindex[$startx];

    #print STDERR "########## $xm $ym $startx $jmin\n";

    for($j=$jmin; $j<@cmpdata; $j++){

	# correct dophot type?
	next if ($check4dophottypeflag && !checkdophottype($type_cmp[$j],\@dophottypes));
	#print STDERR "GGG1\n";

	# S/N good enough?
	next if (($dmag_cmp[$j]>$maxdM) && ($maxdM>0.0));
	#print STDERR "GGG12\n";

	# masking in aperture?
	next if !(hex($mask_cmp[$j] % 32768) == 0);
	#print STDERR "GGG123\n";

	my $xc = $x_cmp[$j];
	my $yc = $y_cmp[$j];

	# don't search further than you need...
	last if ($xc>$xm+$searchrad+1);


	$distance2=($xc-$xm)*($xc-$xm) + ($yc-$ym)*($yc-$ym);
	#print STDERR "FFFFFXXXX $x_cmp[$j] $y_cmp[$j] $distance2\n";
	if ($distance2 < $searchrad2){
	    $Ncmpfound++;
	    if ($distance2<$bestcmpdistance2){
		$bestcmpindex=$j;
		$bestcmpdistance2=$distance2;
	    }
	}
    }


    # modify the cmp line
    if ($Ncmpfound>0){
	# count the dophot types
	$Ntypehash{$type_cmp[$bestcmpindex]}++;
	# skip if if not in usetype!
	if ($check4dophottypeflag && !checkdophottype($type_cmp[$bestcmpindex],\@usedophottypes)){
	    $Ndifferenttype++;
	    next;
	}

	my $newline = $matchlist[$i] . " | ". $cmpdata[$bestcmpindex];
	if ($Ncmpfound==1){
	    $Ngood++;
	    push(@matcheddata,$newline);
	    # save the max to calculate the mag difference
	    push(@mags1,$mag2match[$i]);
	    push(@dmags1,$dmag2match[$i]);
	    push(@mags2,$mag_cmp[$bestcmpindex]);
	    push(@dmags2,$dmag_cmp[$bestcmpindex]);
	    $cmp2catindex{$i}=$bestcmpindex;
	    # this info will be saved
	    push(@mags2compare,"$mag2match[$i] $dmag2match[$i] $mag_cmp[$bestcmpindex] $dmag_cmp[$bestcmpindex] $x2match[$i] $y2match[$i] $x_cmp[$bestcmpindex] $y_cmp[$bestcmpindex]");
	} else {
	    $Nambiguous++;
	    push(@ambiguousmatch,$newline);
	}
    } else {
	$Nbad++;
	push(@nomatch,$matchlist[$i]);
    }

    if (($Ntot % 500 == 0) && ($Ntot>0)) {
	print STDERR sprintf("%5d: %5d(%3.1f\%) matched %5d(%3.1f\%) unmatched %5d(%3.1f\%) different dophot type\n",$Ntot,$Ngood,$Ngood/$Ntot*100.0,$Nbad ,$Nbad/$Ntot*100.0,$Ndifferenttype,$Ndifferenttype/$Ntot*100.0);
    }
}

print STDERR "$Ntypehash{1} $Ntypehash{2}\n";

if ($Ntot<=0){
    printf STDERR "ERROR: Doesn't seem that any of the catalogue stars are on the chip! check your catalogue!\n";
    exit(0);
}


print STDERR sprintf("total: %5d(%3.1f\%) matched %5d(%3.1f\%) unmatched %5d(%3.1f\%) different dophot type\n",$Ngood,$Ngood/$Ntot*100.0,$Nbad ,$Nbad/$Ntot*100.0,$Ndifferenttype,$Ndifferenttype/$Ntot*100.0);
print STDERR sprintf("ambiguous matches: %5d\n",$Nambiguous);


### write out to new cmp file
$outfile = $cmpfile if ($outfile eq "");
$outfilenomatch = $outfile.".unmatched";
$outfilematch = $outfile.".matched";
$outfileambiguous = $outfile.".ambmatch";
$outfileall = $outfile.".allmatch";

chomp(@matcheddata);
chomp(@ambiguousmatch);
@allmatcheddata=(@matcheddata,@ambiguousmatch);

my ($mu,$emu2,$stdev,$chisqrnorm,$clipratio)=&magstats(\@mags1,\@dmags1,\@mags2,\@dmags2,$Nsigma,$maxit);
print STDERR sprintf("MU(cat-cmp): %6.4f\nEMU: %8.3e\nSTDEV: %6.3f\nX2NORM: %6.2f\nPCLIP: %6.2f\%\n",$mu,sqrt($emu2),$stdev,$chisqrnorm,$clipratio*100);

if ($saveabsphotinfo){
    (my $basename = $outfile) =~ s/\.sw\.\Scmp//;
    $basename =~ s/.*\///;
    my @out=(sprintf("#%7s %8s %8s %8s %8s %8s %8s %8s %8s %8s %8s %8s %8s %8s %4s %5s %6s %40s","M","dM","Mcmp","dMcmp","zptmag","dMtot","deltaM","deltaMn","Xcat","Ycat","Xcmp","Ycmp","dX","dY","type","FWHM","photcode","basename"));;
    my @ilist = sort  {$a <=> $b;} (keys %cmp2catindex);
    foreach my $i (@ilist){
	my $j = $cmp2catindex{$i};
	#print STDERR "<$i> <$j>\n";
	my $dMtot = sqrt($dmag2match[$i]*$dmag2match[$i] + $dmag_cmp[$j]*$dmag_cmp[$j]),
	my $deltaM = $mag2match[$i]-($mag_cmp[$j]+$mu);
	my $deltaMn = "-";
	if ($dMtot>0){
	    $deltaMn = $deltaM/$dMtot;
	}
	push(@out,sprintf("%8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f %4d %5.2f 0x%04x %40s",$mag2match[$i],$dmag2match[$i],$mag_cmp[$j]+$mu,$dmag_cmp[$j],$mu,$dMtot,$deltaM,$deltaMn,$x2match[$i],$y2match[$i],$x_cmp[$j],$y_cmp[$j],$x2match[$i]-$x_cmp[$j],$y2match[$i]-$y_cmp[$j],$type_cmp[$j],$FWHM,$photcode,$basename));
    }
    
    my $absphotinfofile .= "$outfile.absphotinfo";
    print STDERR "saving to $absphotinfofile\n";
    &SaveToFile("$absphotinfofile",@out);
}

my $setheadparams = "";

# estimate 3-sigma, 5-sigma, and 10-sigma limit
my ($errorflag,$skysig,$fwhm) = &GetFitsKeywords($cmpfile,"SKYSIG","FWHM");
if ($errorflag){
    print STDERR "ERROR: Could not get SKYSIG and/or FWHM from $cmpfile to calculate M3SIGMA etc\n";
    $setheadparams .= " M3SIGMA='nan' M5SIGMA='nan' M10SIGMA='nan' ";
} else {
    print STDERR "fwhm:$fwhm  skysig:$skysig\n";
    my $Npix_per_FWHM_Area = 2.5*2.5*$fwhm*$fwhm;
    print STDERR "Npix FWHM area: $Npix_per_FWHM_Area\n";
    my $skysig_per_FWHM_Area = sqrt($Npix_per_FWHM_Area * ($skysig*$skysig));
    print STDERR "skysig FWHM area: $skysig_per_FWHM_Area\n";
    $setheadparams .= sprintf(" M3SIGMA=%.4f / 'mag of 3-sigma estimated from SKYSIG' M5SIGMA=%.4f / 'mag of 5-sigma estimated from SKYSIG' M10SIGMA=%.4f / 'mag of 10-sigma estimated from SKYSIG' ",
			      -2.5*log10(3.0*$skysig_per_FWHM_Area)+$mu,
			      -2.5*log10(5.0*$skysig_per_FWHM_Area)+$mu,
			      -2.5*log10(10.0*$skysig_per_FWHM_Area)+$mu);
}

if ($savefiles){
    print "saving to $outfilematch\n";
    SaveToFile($outfilenomatch,@nomatch);
    SaveToFile($outfilematch,@matcheddata);
    SaveToFile($outfileambiguous,@ambiguousmatch);
    SaveToFile($outfileall,@allmatcheddata);
    SaveToFile("$outfile.mags2compare",@mags2compare);
}



$Ntot = 0;
foreach $dophottype (@dophottypes){
    $Ntot += $Ntypehash{$dophottype};
    print STDERR "Matched dophot type $dophottype: $Ntypehash{$dophottype}\n";
}
if ($Ntot>0){
    foreach $dophottype (@dophottypes){
	$setheadparams .= sprintf(" APMTYPE%d=%.4f / 'Fraction of matched objects with dophot type %d'",$dophottype,$Ntypehash{$dophottype}/$Ntot,$dophottype);
	print STDERR sprintf("APMTYPE%d=%.4f\n",$dophottype,$Ntypehash{$dophottype}/$Ntot);
    }
}

# calculate the magnitude(s) which has a certain median uncertainty
if ($MAG_AT_UNCERTAINTY_FLAG){
    print STDERR "### Calculating magnitude(s) which has a certain uncertainty\n";
    my ($errorflag,$stats_ref) = &dMversusM($mu,\@mag_cmp,\@dmag_cmp,\@type_cmp,$MAU_BINSIZE,$MAU_STATSTYPE,$MAU_NITERMAX,$MAU_NSIG,$MAU_NMIN4BIN,$MAU_MAXSTDEVRATIO,\@MAU_TYPES,1);
    if ($errorflag){
	print STDERR "Could not determine the magnitude @ errors !!!!\n";
	exit(0);
    }
    if ($MAU_SAVELIST){
	my @output=("# BINSIZE=$MAU_BINSIZE, STATSTYPE=$MAU_STATSTYPE, NITERMAX=$MAU_NITERMAX, NSIG=$MAU_NSIG, NMIN4BIN=$MAU_NMIN4BIN, MAXSTDEVRATIO=$MAU_MAXSTDEVRATIO, TYPES=".join(",",@MAU_TYPES));
	push(@output,"#M         dM    N stdev");
	my @bs = sort {$a <=> $b} (keys %$stats_ref);
	foreach (0..$#bs){
	    $b = $bs[$_];
	    #print STDERR sprintf("TEST: $_,$bs[$_],($b),%d,,,$$stats_ref{$b}{M}\n",scalar(@bs));;
	    next if ($$stats_ref{$b}{flag}>0);
	    my $outline = sprintf("%7.3f %5.3f %4d %5.3f",$$stats_ref{$b}{M},$$stats_ref{$b}{$MAU_STATSTYPE},$$stats_ref{$b}{N},$$stats_ref{$b}{stdev});
	    #print STDERR "$outline\n";
	    push(@output,$outline);
	}
        print STDERR "Saving M4dM to $cmpfile.M4dM\n";
	&SaveToFile("$cmpfile.M4dM",@output);
    }

    my $dM2Mhash_ref=0;
    if (@MAU_DMAGLIST>0){
	(my $errorflag,$dM2Mhash_ref)= &M4dM($stats_ref,\@MAU_DMAGLIST,$MAU_STATSTYPE,1);
    }
    foreach my $dM (@MAU_DMAGLIST){
	my $fitskey = sprintf("MAU%03.0f",$dM*1000);
	if ($$dM2Mhash_ref{$dM} =~ /UNKNOWN/){
	    $setheadparams .= sprintf(" $fitskey='nan' / 'magnitude with median uncertainty of %.3f'",$$dM2Mhash_ref{$dM},$dM);
	} else {
	    $setheadparams .= sprintf(" $fitskey=%.3f / 'magnitude with median uncertainty of %.3f'",$$dM2Mhash_ref{$dM},$dM);
	}
    }
}

if (&SetFitsKeywords($cmpfile,$setheadparams)){
    print STDERR "ERROR: Could not write $setheadparams to $cmpfile!\n";
    exit(0);
}
print STDERR "Info saved to header of $cmpfile\n";

printf STDERR "SUCCESS\n";

sub pointer2sortedlist{
    my ($nx,@xlist)=@_;
    # create pointers to the sorted lists: makes matching faster...
    # $cmpindex[$xx] is the index of the first measurement, for which x>=$xx
    undef my @cmpindex;
    my $Ncmpobj=@xlist;

    # first, set all pointers to 0
    for(my $x=0;$x<=$nx;$x++){$cmpindex[$x]=0;}

    my $xlast=-1;
    my $lastgoodindex=0;
    for($i=0;$i<$Ncmpobj;$i++){
	my $x= int($xlist[$i]);
	next if ($x < 0.0); # skip negative values. This is taken care of by setting $cmpindex[0]=0 later on
	next if ($x > $nx);
	$lastgoodindex=$i;
	next if ($x == $xlast);
	for (my $xx=$xlast+1;$xx<=$x;$xx++){
	    $cmpindex[$xx]=$i;
	}
	$xlast=$x;

    }

    $cmpindex[0]=0; # make the first index always point to the first entry. Allows negative X values!

    # fillup the rest of cmpindex
    $lastgoodindex++ if ($lastgoodindex+1<$Ncmpobj);
    for (my $xx=$xlast+1;$xx<=$nx;$xx++){
	$cmpindex[$xx]=$lastgoodindex;
    }

    return(@cmpindex);
}

sub xsort{
    my ($x1) = $a =~ /^\s*(\S+)/;
    my ($x2) = $b =~ /^\s*(\S+)/;
    $x1 <=> $x2;
}

sub cat2xy{
    my ($catfilename,$cmpfile)=@_;
#    printf "TEST ($catfilename,$cmpfile)\n";
    my ($header,@catdata)=LoadFromFile($catfilename);
    undef my @tempdata;
    foreach my $line (@catdata){
	next if ($line =~ /^\#/);
	$line =~ s/^\s+//;
	(my $RA,my $DEC)=$line=~/(\S+)\s+(\S+)/;
	push(@tempdata,"$RA $DEC");
    }
#    my $catfilenametemp = $catfilename;
#    $catfilenametemp =~ s/.*\///;	# zap everything before last slash
#    $catfilenametemp.=".delme";
    my $catfilenametemp = "$cmpfile.xycat.delme";
    &SaveToFile($catfilenametemp,@tempdata);
    my $cmd="sky2xy $cmpfile "."@".$catfilenametemp;
    print STDERR "executing: $cmd\n";
    my @xypos=`$cmd`;
    system("rm -f $catfilenametemp");
    chomp(@xypos);
    if ($xypos[0] =~ /linear/){
	print STDERR "ERROR: something is wrong with the astrometric solution of $cmpfile:\n";
	print STDERR "$xypos[0]\n";
	undef @xypos;
    }
    #my ($header,@catdata)=LoadFromFile($catfilename);
    undef my @newdata;
    for(my $i=0;$i<@xypos;$i++){
	next if ($xypos[$i] =~ /nan/);
	$xypos[$i] =~ s/.*->\s+//;
	(my $shiftedx,my $shiftedy)=$xypos[$i]=~/(\S+)\s+(\S+)/;
	push(@newdata,sprintf(" %10.3f %10.3f %s",$shiftedx,$shiftedy,$catdata[$i]));
    }
    return(@newdata);
}


sub checkdophottype{
    my ($type,$dophottypes_ref)=@_;
    my $matchflag=0;my $type2;
    foreach $type2 (@$dophottypes_ref){
	$matchflag=1 if ($type2 == $type);
    }
    return($matchflag);
}

sub magstats{
    my ($mags1_ref,$dmags1_ref,$mags2_ref,$dmags2_ref,$Nsigma,$maxit)=@_;
    my ($mu,$emu2,$stdev,$chisqrnorm,$Nclip);
    $mu=0;
    print STDERR sprintf("I: %-6s %-8s %-6s %-6s %-6s\n","mu","emu","stdev","X2norm","Nclip\%");
    for my $iteration (0..$maxit-1){
	undef @dummyout; #test
	$muold=$mu;
	my $Nsigma_tmp = ($iteration==0) ? 3*$Nsigma : $Nsigma;
	($mu,$emu2,$stdev,$chisqrnorm,$clipratio)=&magstats_sigmacut($mags1_ref,$dmags1_ref,$mags2_ref,$dmags2_ref,$Nsigma_tmp,$mu,$iteration);
	print STDERR sprintf("%d: %7.4f %8.3e %6.3f %6.2f %6.2f\%\n",
			     $iteration,$mu,sqrt($emu2),$stdev,$chisqrnorm,$clipratio*100);
	last if ($Nsigma<=0.0);
	last if (($muold==$mu) && ($iteration>0));
    }
    return($mu,$emu2,$stdev,$chisqrnorm,$clipratio);
}

sub magstats_sigmacut{
    my ($mags1_ref,$dmags1_ref,$mags2_ref,$dmags2_ref,$Nsigma,$mu_old,$iteration)=@_;

    my ($mu,$emu2,$stdev,$chisqrnorm,$clipratio);

    my $N=scalar(@$mags1_ref);

    die "No stars!\n" if ($N<1);

    my $Nsigma2=$Nsigma*$Nsigma;
    my $c1=0;my $c2=0;my $Nused=0;
    undef my @skip;

    if ($iteration>0){
	for my $i (0..$N-1){
	    # Note: a systematic error is added to the photometrc error
	    my $e2=$$dmags1_ref[$i]*$$dmags1_ref[$i]+$$dmags2_ref[$i]*$$dmags2_ref[$i] + $sys_err*$sys_err;
	    $skip[$i]=0;


	    my $delta=($$mags1_ref[$i] - $$mags2_ref[$i] - $mu_old);
	    #print STDERR sprintf("TEST %4d: %.2f %.2f %.2f delta:%.2f errors: %.3f %.3f %.3f %.3f: %f \n",
	    #			 $i,$$mags1_ref[$i],$$mags2_ref[$i],$mu_old,
	    #			 $$mags1_ref[$i] - $$mags2_ref[$i] - $mu_old,
	    #			 $$dmags1_ref[$i],$$dmags2_ref[$i],$sys_err,sqrt($e2),
	    #			 ($delta*$delta)/$e2);
	    if (($delta*$delta)/$e2 > $Nsigma2){
		$skip[$i]=1;
		next;
	    }
	    $Nused++;
	    $c1+=($$mags1_ref[$i] - $$mags2_ref[$i])/$e2;
	    $c2+=1/$e2;
	}
	$clipratio=($N-$Nused)/$N;
	$mu=$c1/$c2;
	$emu2=1.0/$c2;
    } else {
	undef my @diffs;
	for my $i (0..$N-1){
	    push(@diff,($$mags1_ref[$i] - $$mags2_ref[$i]));
	}
	@diff = sort(@diff);
	$clipratio=0.0;
	$mu=$diff[int($N*0.5)];
	$emu2=0.0;
	$Nused=$N;
    }

#    undef my @rrr; #test
    $chisqrnorm=0;my $sumdelta2=0;
    for my $i (0..$N-1){
	#if (($iteration>0) && ($skip[$i]>0)){ #test
	#    push(@dummyout,$dummy[$i]);
	#    print "$dummy[$i]\n";
	#    print sprintf("%12.4f %12.4f ($$mags1_ref[$i] - $$mags2_ref[$i] - $mu)\n",($$mags1_ref[$i] - $$mags2_ref[$i] - $mu),sqrt($$dmags1_ref[$i]*$$dmags1_ref[$i]+$$dmags2_ref[$i]*$$dmags2_ref[$i]));
	#}
	next if (($iteration>0) && ($skip[$i]>0));
	my $e2=$$dmags1_ref[$i]*$$dmags1_ref[$i]+$$dmags2_ref[$i]*$$dmags2_ref[$i] + $sys_err*$sys_err;
	#my $e2=$$dmags1_ref[$i]*$$dmags1_ref[$i]+$$dmags2_ref[$i]*$$dmags2_ref[$i];
	my $delta=($$mags1_ref[$i] - $$mags2_ref[$i] - $mu);
	my $delta2=$delta*$delta;
	$chisqrnorm+=$delta2/$e2;
	$sumdelta2+=$delta2;

    }

    $stdev=sqrt($sumdelta2/($Nused-1));
    $chisqrnorm/=($Nused);
    return ($mu,$emu2,$stdev,$chisqrnorm,$clipratio);
}

sub M4dM{
    my ($stats_ref,$dMaglist_ref,$statstype,$verbose)=@_;
    my @bs = sort {$b <=> $a} (keys %$stats_ref);
    undef my %dM2M;
    foreach my $dM (@$dMaglist_ref){
	$dM2M{$dM}="UNKNOWN";
    }
    if (scalar(@bs)<1){
	return(1,\%dM2M);
    }

    $NdM = scalar(@$dMaglist_ref);
    undef my $b2;
    foreach (0..$#bs){
	$b = $bs[$_];
	#print STDERR sprintf("TEST: $_,$bs[$_],($b),%d,,,$$stats_ref{$b}{M}\n",scalar(@bs));;
	next if ($$stats_ref{$b}{flag}>0);
	my $Nfound = 0;
	foreach my $dM (@$dMaglist_ref){
	    # is this the first iteration?
	    if ($dM2M{$dM} eq "UNKNOWN"){
		if ($$stats_ref{$b}{$statstype}>$dM){
		    $dM2M{$dM} = "BIGGER";
		} else {
		    $dM2M{$dM} = "UNKNOWN,>=$$stats_ref{$b}{M}";
		}
	    }
	    if ($dM2M{$dM} !~ "BIGGER"){
		$b2 = $b;
		$Nfound++;next;
	    }
	    if ($$stats_ref{$b}{$statstype}<$dM){
		if ($b == $#bs){
		    die "BUG!!!!! err_at_mag.pl";
		}
		if ($$stats_ref{$b}{$statstype} == $$stats_ref{$b2}{$statstype}){
		    $dM2M{$dM} = $$stats_ref{$b}{M};
		} else {
		    $dM2M{$dM} = $$stats_ref{$b}{M} + ($dM - $$stats_ref{$b}{$statstype})/($$stats_ref{$b2}{$statstype} - $$stats_ref{$b}{$statstype}) * ($$stats_ref{$b2}{M} - $$stats_ref{$b}{M});
		}
	    } else {
		$dM2M{$dM}="BIGGER,<=$$stats_ref{$b}{M}";
	    }
	}
	$b2 = $b;
	last if ($Nfound == $NdM);
    }
    foreach my $dM (@$dMaglist_ref){
	$dM2M{$dM}=~ s/BIGGER/UNKNOWN/;
	if ($verbose){
	    print STDERR sprintf("dM=%.3f at M=$dM2M{$dM}\n",$dM);
	}
    }
    return(0,\%dM2M);
}


sub dMversusM{
    my ($zptmag,$M_ref,$dM_ref,$type_ref,$binsize,$statstype,$nitermax,$Nsig,$Nmin4bin,$maxstdevratio,$goodtypes_ref,$verbose) = @_;
    undef my %stats;

    if (verbose){
	print STDERR "BINSIZE=$binsize, STATSTYPE=$statstype, NITERMAX=$nitermax, NSIG=$Nsig, NMIN4BIN=$Nmin4bin, MAXSTDEVRATIO=$maxstdevratio, TYPES=".join(",",@$goodtypes_ref)."\n";
    }

    # read in the data, and get the minimum and maximum magnitude
    my $i = 0;
    undef my @M;undef my @dM;
    my $MMIN = 0;my $MMAX = 0;
    foreach my $j (0..$#$M_ref){
	my $keepflag = 0;
	foreach my $goodtype (@$goodtypes_ref){
	    $keepflag = 1 if ($goodtype == ($$type_ref[$j] & 0xf));
	}
	next if (!$keepflag);
	$M[$i]=$$M_ref[$j];
	$dM[$i]=$$dM_ref[$j];
	$M[$i] += $zptmag;
	if ($i == 0){
	    $MMIN = $M[$i];$MMAX = $M[$i];
	}
	$MMIN = $M[$i] if ($M[$i] < $MMIN);
	$MMAX = $M[$i] if ($M[$i] > $MMAX);
	$i += 1;
    }

    # define bins
    $MMIN = floor($MMIN/$binsize)*$binsize;
    $MMAX = ceil($MMAX/$binsize)*$binsize;
    my $NBINS = ceil(($MMAX-$MMIN)/$binsize);
    print STDERR "Mmin:$MMIN Mmax:$MMAX binsize:$binsize Nbins:$NBINS\n";

    # fill up the bins with lists of dM: @{${binhash{$b}}} is a list
    # with the dMs for the magnitude bin centered around
    # M=&bin2M($b,$MMIN,$binsize)
    #
    # &M2bin($M[$i],$MMIN,$binsize,$NBINS) converts a magnitude to the bin index
    # &bin2M($b,$MMIN,$binsize) converts a bin index into the central magnitude of the bin
    undef my %binhash;
    foreach my $i (0 .. $#M){
	push(@{${binhash{&M2bin($M[$i],$MMIN,$binsize,$NBINS)}}},$dM[$i]);
    }


    print STDERR "#bin   X:       M    dM    N stdev\n";
    print STDERR "DDDD: $NBINS\n";
    my $iteration;
    foreach my $b (0 .. $NBINS-1){
	# don't even bother if there are not enough measuremnts in bin
	if (scalar(@{${binhash{$b}}})<$Nmin4bin){
	    $stats{$b}{flag} = 1;
	    next;
	}

	# get the first set of statistics, no sigma-clip yet
	my $stat = Statistics::Descriptive::Full->new();
	$stat->add_data(@{${binhash{$b}}});
	$stats{$b}{$statstype} = $stat->$statstype();
	$stats{$b}{stdev}  = $stat->standard_deviation();
	$stats{$b}{N}      = $stat->count();
	$stats{$b}{M}      = &bin2M($b,$MMIN,$binsize);
	#print STDERR sprintf("bin $b/0 ($stats{$b}{N}): M=%f N=%4d mean:%.3f median:%.3f mode:%.3f stdev:%.3f\n",$stats{$b}{M},scalar(@{${binhash{$b}}}),$stats{$b}{mean},$stats{$b}{median},$stats{$b}{mode},$stats{$b}{stdev});

	# make the sigma-clip
	if ($Nsig>0.0){
	    for ($iteration=1;$iteration<=$nitermax;$iteration++){
		last if ($stats{$b}{stdev} <= 0.0);
		my $Nused_old = $stats{$b}{N};
		undef my @newdM;
		for my $i (0 .. $#{${binhash{$b}}}){
		    my $dM = ${${binhash{$b}}}[$i];
		    if ( (abs($dM-$stats{$b}{$statstype})/$stats{$b}{stdev}) < $Nsig) {
			push(@newdM,$dM);
		    }

		}
		$stat = Statistics::Descriptive::Full->new();
		$stat->add_data(@newdM);
		#$stats{$b}{mean}   = $stat->mean();
		#$stats{$b}{mode}   = $stat->mode();
		#$stats{$b}{median} = $stat->median();
		$stats{$b}{$statstype} = $stat->$statstype();
		$stats{$b}{stdev}  = $stat->standard_deviation();
		$stats{$b}{N}      = $stat->count();
		$stats{$b}{M}      = &bin2M($b,$MMIN,$binsize);
		if ($stats{$b}{N} >= $Nused_old){
		    last;
		}
	    }
	}

	# make some cuts
	if ($stats{$b}{N}<$Nmin4bin){
	    $stats{$b}{flag} = 2;
	    next;
	}
	if ($MAXSTDEVRATIO * $stats{$b}{stdev}> $stats{$b}{$statstype}){
	    $stats{$b}{flag} = 3;
	    next;
	}
    }
    if ($verbose>0){
	foreach my $b (0 .. $NBINS-1){
	    next if ($stats{$b}{flag}>0);
	    print STDERR sprintf("bin %4d: %7.4f %5.4f %4d %5.4f\n",$b,$stats{$b}{M},$stats{$b}{$statstype},$stats{$b}{N},$stats{$b}{stdev});
	}
    }
    return(0,\%stats);

}


sub M2bin{
    my ($M,$Mmin,$binsize,$Nbin) = @_;
    my $bin = int(($M - ($Mmin - 0.5*$binsize))/$binsize);
    $bin = 0 if ($bin < 0);
    $bin = ($Nbin-1) if ($bin > $Nbin-1);
    return($bin);
}

sub bin2M{
    my ($M,$Mmin,$binsize) = @_;
    return($Mmin + $M * $binsize);
}

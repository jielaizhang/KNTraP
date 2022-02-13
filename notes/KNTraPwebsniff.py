#!/usr/bin/env python

import re,sys,string,math,os,types,copy,time,stat,glob
# put the tools directory into the path
sys.path.append(os.environ['PIPE_PYTHONSCRIPTS'])
sys.path.append(os.environ['PIPE_PYTHONSCRIPTS']+'/tools')
import matplotlib
#matplotlib.use('Agg')
import texttable,pipeclasses,tools,matplot
import fcntl
import genericprocs as gen
import pipedefs as defs
from genericprocs import *
from astropy.time import Time

def f2name(photcode):
    import types
    if isinstance(photcode,str):
        photcode = eval(photcode)
    band = photcode & 0xff
    filters = {0 : 'VR',
               1 : 'U',
               2 : 'B',
               3 : 'V',
               4 : 'R',
               5 : 'I',
               0x13 : 'g',
               0x14 : 'r',
               0x15 : 'i',
               0x16 : 'z',
               0x17 : 'y'}

    return filters[band]

def addlink2string(s,link):
    return('<a href="%s">%s</a>' % (link,s))

def imagestring4web(imagename,width=None,height=None):
    imstring = '<img src="%s"' % os.path.basename(imagename)
    if height != None:
        if isinstance(height,int): height = str(height)
        #if type(height) is types.IntType: height = str(height)
        imstring += 'height=%s' % height
    if width != None:
        if isinstance(width,int): width = str(width)
        #if type(width) is types.IntType: width = str(width)
        imstring += 'width=%s' % width
    imstring +='>'
    return(imstring)


class dumbhtmltable:
    def __init__(self,Ncols,cellpadding=2,cellspacing=2,border=1,width='100%',height=None,align='center',optionalarguments=''):
        self.Ncols = Ncols
        self.cellpadding = cellpadding
        self.cellspacing = cellspacing
        self.border      = border
        self.width       = width
        self.height      = height
        self.align       = align
        self.optionalarguments  = optionalarguments
        self.body = []

    def startrow(self,style = ''):
        self.body.append('<tr %s>' % style)
    def endrow(self):
        self.body.append('</tr>\n')

    def addcol(self,colval,link=None, verticalalign='top', textalign='center',
               bold=None, italic=None, underline = None, fontsize=None, width=None, height=None, color = None, bgcolor = None):
        if colval is None:
            colval = '-'  # placeholder!

        if link != None:
            colval = '<a href="%s">%s</a>' % (link,colval)

        pre   = ''
        after = ''
        #if textalign != None:
        #    pre   += '<%s>'  % (textalign)
        #    after  = '</%s>' % (textalign) + after
        if fontsize != None:
            if isinstance(fontsize,str): fontsize = int(fontsize)
            pre   += '<font size=%d>' % (fontsize)
            after  = '</font>' + after
        if bold != None and bold != 0:
            pre   += '<b>'
            after  = '</b>'
        if  underline != None and underline != 0:
            pre   += '<u>'
            after  = '</u>'
        if italic != None and italic != 0:
            pre   += '<b>'
            after  = '</b>'
        if color != None:
            if isinstance(color,int): color = str(color)
            #if type(color) is types.IntType: color = str(color)
            pre   += '<font color=%s>' % (color)
            after  = '</font>' + after
        #if bgcolor != None:
        #    if type(bgcolor) is types.IntType: bgcolor = str(bgcolor)
        #    pre   += '<font bgcolor=%s>' % (bgcolor)
        #    after  = '</font>' + after

        line = '<td'
        if textalign != None:
            line += ' ALIGN="%s"' % textalign
        if width != None:
            if isinstance(width,int): width = str(width)
            #if type(width) is types.IntType: width = str(width)
            line += ' WIDTH="%s"' % width
        if height != None:
            if isinstance(height,int): height = str(height)
            #if type(height) is types.IntType: height = str(height)
            line += ' HEIGHT="%s"' % height
        if verticalalign != None:
            line += ' VALIGN="%s"' % verticalalign
        if bgcolor != None:
            if isinstance(bgcolor,int): bgcolor = str(bgcolor)
            #if type(bgcolor) is types.IntType: bgcolor = str(bgcolor)
            line += 'BGCOLOR="%s"' % (bgcolor)
        if line != '<td':
            line += ' NOSAVE'
        line += '>'
        line += pre + colval + after + '</td>'

        self.body.append(line)

    def gettable(self):
        t=['<table COLS=%d BORDER=%d CELLSPACING=%d CELLPADDING=%d ALIGN="%s" WIDTH="%s" %s' % (self.Ncols,self.border,self.cellspacing,self.cellpadding,
                                                                                                self.align,self.width,self.optionalarguments)]
        t.extend(self.body)
        t.append('</table>')
        return(t)

class webpageclass:
    def __init__(self):
        self.lines=[]
    def substituteplaceholder(self, pattern2find, newlines,count=0):
        patternobject = re.compile(pattern2find)
        if isinstance(newlines,str):
       # if type(newlines) is types.StringType:
            s = newlines
        elif isinstance(newlines,list):
        #elif type(newlines) is types.ListType:
            s = '\n'.join(newlines)
        else:
            raise RuntimeError('Error: unknown type, dont know how to deal with ',newlines)
        for i in range(len(self.lines)):
            self.lines[i] = patternobject.sub(s,self.lines[i])

    def loaddefaultpage(self,filename,startstring=None,endstring=None):
        if not os.path.isfile(filename):
            raise RuntimeError('ERROR: could not find file '+filename)
        self.lines = open(filename).readlines()
        if startstring != None or endstring != None:
            start = 0
            end = len(self.lines)-1
            if startstring != None:
                patternobject = re.compile(startstring)
                for i in range(len(self.lines)):
                    if patternobject.search(self.lines[i]):
                        start = i+1
                        break
            if endstring != None:
                patternobject = re.compile(endstring)
                for i in range(len(self.lines)):
                    if patternobject.search(self.lines[i]):
                        end = i
                        break
            if (end<start):
                self.lines = []
            else:
                self.lines = self.lines[start:end]


    def savepage(self,filename):
        f = open(filename,'w')
        f.writelines(self.lines)
        f.close()

class websniffclass:
    def __init__(self):
        self.params           = pipeclasses.paramfileclass()

        # all possible features
        self.allfeatures =      ['forcedphot','gettmpldet','datfile','imfinder','tmplfinder','fitsfinder','PSall','PShighSN','PSlast',
                                 'PSseries','difflc','all_t_difflc','maglc','fitparams','tmplfluxinfo',
                                 'xyplotbig','xyplotsmall','linkxyplotbig','linkxyplotsmall','spectrainfo',
                                 'classifybuttons','eventstats']

        self.features  = None
        self.candfile  = None
        self.paramfile = None

        self.transmask     = pipeclasses.transtypeclass()

    def initcandfile(self,candfilename, skipcheckintegrity=0, skipcorrectfluxes=False):
        self.candfile = pipeclasses.lclistclass()
        print('Loading candfile ',candfilename)
        self.candfile = pipeclasses.loadlclist(self.candfile,candfilename, skipcheckintegrity=1, skipcorrectfluxes=True) #should only check integrity once!!
        if self.candfile == None:
            raise RuntimeError('ERROR: could not load object file for %s' % candfilename)

        #self.candfile.filetable.configcols(['photcode','class'],'x','0x%08x')
        self.candfile.filetable.configcols(['photcode'],'x','0x%08x')
        if self.candfile.colexist('alerttable'):
            self.candfile.configcols(['alerttable'],'x','0x%08x')
        self.candfile.configcols(['ID'],'d','%d')
        self.candfile.filetable.configcols(['MJD'],'f','%.5f')
        if not skipcheckintegrity:
            self.candfile.check_list_integrity()
        if not skipcorrectfluxes:
            self.candfile.adjustFluxesErrors(fix4chi2=True, adjDiffFluxerr=False, addSys=True, correct4ZPT=True)

    def initcand(self,candkey):
        self.candkey = candkey
        self.id      = self.candfile.getentry(self.candkey, 'ID')
        self.canddifflc = self.candfile.difflc(candkey)
        self.candreglc = self.candfile.reglc(candkey)
        self.canddifflc.configcols(['flux','dflux'],'f','%.2f')
        self.canddifflc.configcols(['type'],'x','0x%08x')
        self.candreglc.configcols(['flux','dflux'],'f','%.2f')
        self.candreglc.configcols(['type'],'x','0x%08x')

    def initparams(self,paramfile=None):
        if paramfile!=None:
            self.params.loadfile(paramfile)
        if self.paramfile!=None:
            self.params.loadfile(self.paramfile,addflag=1)


        if len(self.params.allrowkeys)==0:
            if 'PIPE_PARAMS' in os.environ:
                self.params.loadfile(os.environ['PIPE_PARAMS'])
            else:
                raise RuntimeError('ERROR: no parameter file specified!')

        if self.params.get('TRANSMASKFILE')!='':
            print('Loading ',self.params.get('TRANSMASKFILE'))
            self.transmask.loadfile(self.params.get('TRANSMASKFILE'))

    # make sure that the features are valid!
    def checkfeatures(self):
        if tools.AnotB(self.features,self.allfeatures):
            print('ERROR: unkown feature(s) specified: %s' % ' '.join(tools.AnotB(self.features,self.allfeatures)))
            sys.exit(0)

    def addimage2webpage(self,webpage,imagename,placeholder,width=None,height=None):
        imstring = '<img src="%s"' % os.path.basename(imagename)
        if height != None:
            if isinstance(height,int): height = str(height)
            #if type(height) is types.IntType: height = str(height)
            imstring += 'height=%s' % height
        if width != None:
            if isinstance(width,int): width = str(width)
            #if type(width) is types.IntType: width = str(width)
            imstring += 'width=%s' % width
        imstring +='>'
        webpage.substituteplaceholder(placeholder,imstring)

    def addimage2webpage_recursive(self,webpage,imagename,placeholder,width=None,height=None):
        imstring = '<img src="%s"' % os.path.basename(imagename)
        if height != None:
            if isinstance(height,int): height = str(height)
            #if type(height) is types.IntType: height = str(height)
            imstring += 'height=%s' % height
        if width != None:
            if isinstance(width,int): width = str(width)
            #if type(width) is types.IntType: width = str(width)
            imstring += 'width=%s' % width
        imstring +='>'
        webpage.substituteplaceholder(placeholder,imstring+placeholder)

    def makedifflc(self, difflc_fig, webpage, MJDmin=None, MJDmax=None, MJDsub=0.0,dofits=None,title=None,ylabel=None,onlyforced=0,onlynonforced=0,Nmaskmax=None):
        errorflag = 0
        #(MJDmin, MJDmax) = getMJDrange4year(self.params.get_asint('A_YEAR'))
        if MJDsub is None: MJDsub = getMJDsub4year(self.params.get_asint('A_YEAR'))
        lckeyshash={}
        #self.candfile.difflc(self.candkey).printtxttable()
        for photcode in self.params.gethexlist('A_LC_PHOTCODES'):
            keys = self.candfile.difflc(self.candkey).selectlckeys(photcodes=[photcode],dophottypes=[1,7],
                                                                   onlyforced=onlyforced,onlynonforced=onlynonforced,
                                                                   MJDmin=MJDmin, MJDmax=MJDmax,Nmaskmax=Nmaskmax)
            lckeyshash[photcode]=keys
        #    print('VVVVVVVVV',photcode,keys,MJDmin,MJDmax)
        #sys.exit(0)
        if ylabel==None:
            ylabel='difference flux'
        matplot.makelcplot(self.candfile.difflc(self.candkey), lckeyshash, difflc_fig,
                           MJDmin=MJDmin, MJDmax=MJDmax, MJDsub=MJDsub,
                           title=title, ylabel=ylabel)
        return errorflag

    def makemaglc(self, maglc_fig, webpage, MJDmin=None, MJDmax=None, MJDsub=0.0,dofits=None,title=None,ylabel=None,onlyforced=1,onlynonforced=0,Nmaskmax=None):
        errorflag = 0
        #(MJDmin, MJDmax) = getMJDrange4year(self.params.get_asint('A_YEAR'))
        if MJDsub is None: MJDsub = getMJDsub4year(self.params.get_asint('A_YEAR'))
        lckeyshash={}
        for photcode in self.params.gethexlist('A_LC_PHOTCODES'):
            keys = self.candfile.difflc(self.candkey).selectlckeys(photcodes=[photcode],dophottypes=[1,7],
                                                                   onlyforced=onlyforced,onlynonforced=onlynonforced,
                                                                   MJDmin=MJDmin, MJDmax=MJDmax,Nmaskmax=Nmaskmax)
            lckeyshash[photcode]=keys

        if ylabel==None:
            ylabel='mag'
 
        matplot.makemagplot(self.candfile.difflc(self.candkey), lckeyshash, maglc_fig,
                           MJDmin=MJDmin, MJDmax=MJDmax, MJDsub=MJDsub,
                           title=title, ylabel=ylabel)
        return errorflag

    def makedatfile(self,datfilename,webpage,onlyforced=0,onlynonforced=0):
        errorflag = 0
        #(MJDmin, MJDmax) = getMJDrange4year(self.params.get_asint('A_YEAR'))
        lckeyshash={}
        lc = self.candfile.difflc(self.candkey)
        lc.configcols(['m','dm'],'f','%.3f',visible=1)
        lc.configcols(['MJD'],'f','%.6f',visible=1)
        lc.configcols(['photcode'],'x','0x%04x',visible=1)
        lc.configcols(['filt'],'s','%s',visible=1)
        lc.configcols(['dateobs'],'s','%s',visible=1)
        lc.configcols(['tmpl','ra','dec'],'s','%s',visible=1)
        
        allkeys=[]
        for photcode in self.params.gethexlist('A_LC_PHOTCODES'):
            keys = self.candfile.difflc(self.candkey).selectlckeys(photcodes=[photcode],dophottypes=[1,7],
                                                                   onlyforced=onlyforced,onlynonforced=onlynonforced)
            lckeyshash[photcode]=keys
            allkeys.extend(keys)
            for key in keys:
                flux = lc.getentry(key,'flux_c')
                dflux = lc.getentry(key,'dflux_c')
                zpt = lc.getentry(key,'ZPTMAG_c')
                if (flux is not None) and (dflux is not None) and (flux>=3.0*dflux):
                    m = -2.5 * math.log10(flux)+zpt
                    dm = 2.5 / math.log(10.0) * dflux / flux
                else:
                    m=None
                    dm=None
                lc.setentry(key,'m',m)
                lc.setentry(key,'dm',dm)
                lc.setentry(key,'photcode',photcode & 0xffff)
                try:
                    lc.setentry(key,'filt',f2name(photcode & 0xffff))
                except:
                    lc.setentry(key,'filt',None)
                dateobjects = Time(lc.getentry(key,'MJD'), format='mjd')
                lc.setentry(key,'dateobs',dateobjects.to_value('isot'))
                lc.setentry(key,'tmpl',lc.getentry(key,'fileinfo')['TMPLNAME'])
                lc.setentry(key,'ra',self.candfile.getentry(self.candkey,'RAaverage'))
                lc.setentry(key,'dec',self.candfile.getentry(self.candkey,'DECaverage'))
                #sys.exit(0)
                    
            #lc.printtxttable(keys=keys,cols=['MJD','flux_c','dflux_c','ZPTMAG_c','m','dm'])
            #lc.printtxttable(keys=keys,showallcols=1)
        lc.save2file(datfilename,keys=allkeys,cols=['MJD','dateobs','photcode','filt','flux_c','dflux_c','type','chisqr','ZPTMAG_c','m','dm','ra','dec','cmpfile','tmpl'])
        return errorflag



    def makePSall(self, filekeys, PSall_fig):
        if self.params.get('WS_DOPSALL')=='' and self.params.get('WS_DOPSALL')==0:
            return 0

        images = []
        for filekey in filekeys:
            images.append(self.candfile.filetable.subfitsname(filekey))
        if images == []:
            tools.rmfile(PSall_fig)
            print('Warning: Could not find any diffims! skipping creation of subgifall')
            return 1
        MJDsub = getMJDsub4year(self.params.get_asint('A_YEAR'))
        tools.writeAllImages(PSall_fig, images, None, self.candfile.getentry(self.candkey,'RAaverage'), self.candfile.getentry(self.candkey,'DECaverage'),MJDbase=MJDsub)
        del images
        print('postage stamps %s created ...' % PSall_fig)
        return 0


    def makePS(self, filekeys, PS_fig, nX=8):

        images=[]
        for filekey in filekeys:
            print(self.candfile.filetable.subfitsname(filekey))
            images.append(self.candfile.filetable.subfitsname(filekey))

        if images == []:
            tools.rmfile(PS_fig)
            print('Warning: Could not find any diffims! skipping creation of %s' % PS_fig)
            return 1

        MJDsub = getMJDsub4year(self.params.get_asint('A_YEAR'))
        tools.writeAllImages(PS_fig, images, None, self.candfile.getentry(self.candkey,'RAaverage'), self.candfile.getentry(self.candkey,'DECaverage'),MJDbase=MJDsub,nX=nX)
        del images
        print('postage stamps %s created ...' %   PS_fig)
        return 0

    # make
    #####################
    # add

    def adddifflcall2eventpage(self, webpage, placeholder, difflc_fig, width=None,height=None):
        if 'all_t_difflc' in self.features:
            tools.rmfile(difflc_fig)
            self.makedifflc(difflc_fig, webpage, MJDmin=None, MJDmax=None,
                            MJDsub = self.params.get_asfloat('A_MJDSUB'), dofits = 0)
            self.addimage2webpage(webpage,difflc_fig,placeholder,width=width,height=height)
        else:
            webpage.substituteplaceholder(placeholder,'')

    def adddifflc2eventpage(self, webpage, placeholder, difflc_fig, width=None,height=None,title=None,ylabel=None,onlyforced=0,onlynonforced=0,Nmaskmax=None):
        errorflag = 0
        if 'difflc' in self.features:
            tools.rmfile(difflc_fig)
            MJDrange = gen.getMJDrange4year(self.year)
            MJDmin = self.MJD-120.0
            MJDmax = self.MJD+40.0
            #MJDmin = None
            #MJDmax = None
            #errorflag = self.makedifflc(difflc_fig, webpage, MJDmin = MJDrange[0], MJDmax = MJDrange[1],
            errorflag = self.makedifflc(difflc_fig, webpage, MJDmin = MJDmin, MJDmax = MJDmax,
                                        MJDsub = self.params.get_asfloat('A_MJDSUB'), dofits = self.params.get_asint('WS_DO_FITS'),
                                        title=title, ylabel=ylabel,onlyforced=onlyforced, onlynonforced=onlynonforced,Nmaskmax=Nmaskmax)
            self.addimage2webpage(webpage,difflc_fig,placeholder,width=width,height=height)
            print(difflc_fig)
        else:
            webpage.substituteplaceholder(placeholder,'')
        return errorflag

    def addmaglc2eventpage(self, webpage, placeholder, linkplaceholder, maglc_fig, width=None,height=None,title=None,ylabel=None,onlyforced=0,onlynonforced=0):
        errorflag = 0
        if 'maglc' in self.features:
            tools.rmfile(maglc_fig)
            MJDrange = gen.getMJDrange4year(self.year)
            MJDmin = self.MJD-120.0
            MJDmax = self.MJD+40.0
            #MJDmin = None
            #MJDmax = None
           #errorflag = self.makedifflc(difflc_fig, webpage, MJDmin = MJDrange[0], MJDmax = MJDrange[1],
            errorflag = self.makemaglc(maglc_fig, webpage, MJDmin = MJDmin, MJDmax = MJDmax,
                                        MJDsub = self.params.get_asfloat('A_MJDSUB'), dofits = self.params.get_asint('WS_DO_FITS'),
                                        title=title, ylabel=ylabel,onlyforced=onlyforced, onlynonforced=onlynonforced)
            self.addimage2webpage(webpage,maglc_fig,placeholder,width=width,height=height)
            print(maglc_fig)
        else:
            webpage.substituteplaceholder(placeholder,'')
        webpage.substituteplaceholder(placeholder,'')
        webpage.substituteplaceholder(linkplaceholder,'')
        return errorflag

    def adddatfile2eventpage(self, webpage, linkplaceholder, forceddatfilename, unforceddatfilename):
 #  , onlyforced=0, onlynonforced=0):
        errorflag = 0
        if 'datfile' in self.features:
            tools.rmfile(forceddatfilename)
            print('Saving forced lc data to ascii file:',forceddatfilename)
            errorflag = self.makedatfile(forceddatfilename, webpage, onlyforced=1, onlynonforced=0)
            linkstring = addlink2string('forcedlc',os.path.basename(forceddatfilename))

            tools.rmfile(unforceddatfilename)
            print('Saving unforced lc data to ascii file:',unforceddatfilename)
            errorflag = self.makedatfile(unforceddatfilename, webpage, onlyforced=0, onlynonforced=1)
            linkstring += '   ' + addlink2string('unforcedlc',os.path.basename(unforceddatfilename))

            webpage.substituteplaceholder(linkplaceholder,linkstring)
        else:
            webpage.substituteplaceholder(linkplaceholder,'')
        return errorflag
    
    def addPSall2eventpage(self,eventwebpage,placeholder,placeholderlink,width=None,height=None):

        if 'PSall' in self.features:
            if self.params.get('WS_DOPSALL')=='' and self.params.get('WS_DOPSALL')==0:
                eventwebpage.substituteplaceholder(placeholder,'')
                return 0
            self.candfile.filetable.configcols(['photcode'],'x','0x%08x')
            photcodes= self.candfile.filetable.col_as_list('photcode')
            photcodes = tools.unique([(tools.hex2int(x) & self.candfile.params.get_ashex('FLAG_PHOTCODE_PURE')) for x in photcodes])
            if self.params.get('A_PSSERIES_PHOTCODES')!='':
                photcodes2use = self.params.gethexlist('A_PSSERIES_PHOTCODES')
                photcodes = tools.AandB(photcodes,photcodes2use)

            redo=0
            for photcode in photcodes:
                if not os.path.isfile(self.PSallfig(photcode)):
                    redo = 1
                    break
            lckeys  = self.canddifflc.selectlckeys(dophottypes=[1],onlyforced=1,Nmaskmax=self.params.get('WS_NMASKMAX'))
            filekeys = self.canddifflc.col_asint_list('filetablekey',keys = lckeys)
            # get the files within the correct MJD range if required
            if self.params.get('WS_DELTATIME4PSALL')!=None:
                #self.candfile.filetable.printtxttable(cols=['cmpfile','MJD'])
                #print self.MJD,self.params.get_asfloat('WS_DELTATIME4PSALL'),self.MJD-self.params.get_asfloat('WS_DELTATIME4PSALL'),self.MJD+self.params.get_asfloat('WS_DELTATIME4PSALL')
                filekeys = self.candfile.filetable.CUT_inrange('MJD',self.MJD-self.params.get_asfloat('WS_DELTATIME4PSALL'),self.MJD+self.params.get_asfloat('WS_DELTATIME4PSALL'),keys=filekeys)
            filekeys = self.candfile.filetable.sortkeysbycols(filekeys,'MJD',asstring=0)

            imagestring = ''
            #linkstring = ''
            linktable=dumbhtmltable(len(photcodes),border=0,cellspacing=0,cellpadding=2)
            linktable.startrow()
            string4links = ''

            for photcode in photcodes:
                PSall_fig = self.PSallfig(photcode)
                filekeys4photcode = []
                for filekey in filekeys:
                    
                    if (self.candfile.filetable.getentry(filekey,'photcode') & 0xf00ffff) == (photcode | self.params.get_ashex('FLAG_PHOTCODE_DIFFIM')):
                        filekeys4photcode.append(filekey)

                if len(filekeys4photcode)==0:
                    print('Warning: Could not find any diffims! skipping creation of PSall for photcode 0x%x' % photcode)
                    tools.rmfile(PSall_fig)
                    continue

                if redo:
                    if (not os.path.isfile(PSall_fig)):
                        print('### Creating all postage stamps:',PSall_fig)
                        errorflag = self.makePSall(filekeys4photcode,PSall_fig)
                        if errorflag:
                            print('ERROR: something went wrong with the all PS %s!' % (PSall_fig))
                            tools.rmfile(PSall_fig)
                            eventwebpage.substituteplaceholder(placeholder,'error: something went wrong while creating the epoch series!')
                            return 1
                del filekeys4photcode
                imagestring += imagestring4web(PSall_fig,width=width,height=height)
                linkstring = addlink2string('%s' % (f2name(photcode)),os.path.basename(PSall_fig))
                linktable.addcol(linkstring,textalign='left')
                string4links += ' '+linkstring+' '
                #linkstring += addlink2string('more substamps for %s    ' % (f2name(photcode)),os.path.basename(PSall_fig))
            linktable.endrow()
            eventwebpage.substituteplaceholder(placeholder,imagestring)
            #eventwebpage.substituteplaceholder(placeholderlink,linktable.gettable())
            eventwebpage.substituteplaceholder(placeholderlink,string4links)

    def addPSlast2eventpage(self,eventwebpage,placeholder,width=None,height=None):

        if 'PSlast' in self.features:
            if self.params.get('WS_DOPSLAST')=='' and self.params.get('WS_DOPSLAST')==0:
                eventwebpage.substituteplaceholder(placeholder,'')
                return 0
            self.candfile.filetable.configcols(['photcode'],'x','0x%08x')
            photcodes= self.candfile.filetable.col_as_list('photcode')
            photcodes = tools.unique([(tools.hex2int(x) & self.candfile.params.get_ashex('FLAG_PHOTCODE_PURE')) for x in photcodes])
            if self.params.get('A_PSSERIES_PHOTCODES')!='':
                photcodes2use = self.params.gethexlist('A_PSSERIES_PHOTCODES')
                photcodes = tools.AandB(photcodes,photcodes2use)

            redo=0
            for photcode in photcodes:
                if not os.path.isfile(self.PSlastfig(photcode)):
                    redo = 1
                    break

            lckeys  = self.canddifflc.selectlckeys(dophottypes=[1],onlyforced=1,Nmaskmax=self.params.get('WS_NMASKMAX'))
            filekeys = self.canddifflc.col_asint_list('filetablekey',keys = lckeys)
            filekeys = self.candfile.filetable.sortkeysbycols(filekeys,'MJD',asstring=0)
            #self.candfile.filetable.printtxttable(cols=['MJD'],keys=filekeys)
            #for lckey in lckeys:
            #    filekey = self.canddifflc.getentry(lckey,'filetablekey')
            #    filekeys.append(filekey)
            #    print self.candfile.filetable.getentry(filekey,'MJD'),self.canddifflc.fileinfo(lckey,'MJD')

            imtable=dumbhtmltable(1,border=0,cellspacing=0,cellpadding=0)
            for photcode in photcodes:
                PSlast_fig = self.PSlastfig(photcode)
                filekeys4photcode = []
                for filekey in filekeys:
                    if (self.candfile.filetable.getentry(filekey,'photcode') & 0xf00ffff) == (photcode | self.params.get_ashex('FLAG_PHOTCODE_DIFFIM')):
                        filekeys4photcode.append(filekey)

                if len(filekeys4photcode)==0:
                    print('Warning: Could not find any diffims! skipping creation of PSlast for photcode 0x%x' % photcode)
                    tools.rmfile(PSlast_fig)
                    continue

                nXgif=4
                if self.params.get('WS_N4PSLAST')!=None and len(filekeys4photcode)>self.params.get_asint('WS_N4PSLAST'):
                    nXgif = self.params.get_asint('WS_N4PSLAST')
                    if nXgif<len(filekeys4photcode):
                        filekeys4photcode = filekeys4photcode[-nXgif:]

                if redo:
                    if (not os.path.isfile(PSlast_fig)):
                        print('### Creating epoch of postage stamps:',PSlast_fig)
                        errorflag = self.makePS(filekeys4photcode,PSlast_fig, nX=nXgif)
                        if errorflag:
                            print('ERROR: something went wrong with the epoch series %s!' % (PSlast_fig))
                            tools.rmfile(PSlast_fig)
                            eventwebpage.substituteplaceholder(placeholder,'error: something went wrong while creating the epoch series!')
                            return 1
                del filekeys4photcode
                imtable.startrow()
                imtable.addcol(imagestring4web(PSlast_fig,width=width,height=height),textalign='left')
                imtable.endrow()
                #imagestring += imagestring4web(PSlast_fig,width=width,height=height)
            eventwebpage.substituteplaceholder(placeholder,imtable.gettable())
            del imtable

    def addPShighSN2eventpage(self,eventwebpage,placeholder,width=None,height=None):

        if 'PShighSN' in self.features:
            if self.params.get('WS_DOPSHIGHSN')=='' and self.params.get('WS_DOPSHIGHSN')==0:
                eventwebpage.substituteplaceholder(placeholder,'')
                return 0
            self.candfile.filetable.configcols(['photcode'],'x','0x%08x')
            photcodes= self.candfile.filetable.col_as_list('photcode')
            photcodes = tools.unique([(tools.hex2int(x) & self.candfile.params.get_ashex('FLAG_PHOTCODE_PURE')) for x in photcodes])
            if self.params.get('A_PSSERIES_PHOTCODES')!='':
                photcodes2use = self.params.gethexlist('A_PSSERIES_PHOTCODES')
                photcodes = tools.AandB(photcodes,photcodes2use)

            redo=0
            for photcode in photcodes:
                if not os.path.isfile(self.PShighSNfig(photcode)):
                    redo = 1
                    break
            lckeys  = self.canddifflc.selectlckeys(dophottypes=[1],onlyforced=1,Nmaskmax=self.params.get('WS_NMASKMAX'))
            lckeys  = self.canddifflc.CUT_inrange(defs.lc_fluxcol,0.0,None,keys=lckeys)
            self.canddifflc.configcols(['dM'],'f','%.3f')
            lckeys  = self.canddifflc.sortkeysbycols(lckeys,'dM',asstring=0)
            #self.canddifflc.printtxttable(cols=['dM','flux','dflux','MJD','cmpfile'],keys=lckeys)
            filekeys = self.canddifflc.col_asint_list('filetablekey',keys = lckeys)
            #self.candfile.filetable.printtxttable(cols=['MJD','cmpfile'],keys=filekeys)

            imtable=dumbhtmltable(1,border=0,cellspacing=0,cellpadding=0)
            for photcode in photcodes:
                PShighSN_fig = self.PShighSNfig(photcode)
                filekeys4photcode = []
                for filekey in filekeys:
                    if (self.candfile.filetable.getentry(filekey,'photcode') & 0xf00ffff) == (photcode | self.params.get_ashex('FLAG_PHOTCODE_DIFFIM')):
                        filekeys4photcode.append(filekey)

                if len(filekeys4photcode)==0:
                    print('Warning: Could not find any diffims! skipping creation of PShigh for photcode 0x%x' % photcode)
                    tools.rmfile(PShighSN_fig)
                    continue

                nXgif=8
                if self.params.get('WS_N4PSHIGHSN')!=None and len(filekeys4photcode)>self.params.get_asint('WS_N4PSHIGHSN'):
                    nXgif = self.params.get_asint('WS_N4PSHIGHSN')
                    if nXgif<len(filekeys4photcode):
                        filekeys4photcode = filekeys4photcode[:nXgif]

                if redo:
                    if (not os.path.isfile(PShighSN_fig)):
                        print('### Creating epoch of postage stamps:',PShighSN_fig)
                        errorflag = self.makePS(filekeys4photcode,PShighSN_fig, nX=nXgif)
                        if errorflag:
                            print('ERROR: something went wrong with the epoch series %s!' % (PShighSN_fig))
                            tools.rmfile(PShighSN_fig)
                            eventwebpage.substituteplaceholder(placeholder,'error: something went wrong while creating the epoch series!')
                            return 1
                del filekeys4photcode
                imtable.startrow()
                imtable.addcol(imagestring4web(PShighSN_fig,width=width,height=height),textalign='left')
                imtable.endrow()
                #imagestring += imagestring4web(PShighSN_fig,width=width,height=height)
            eventwebpage.substituteplaceholder(placeholder,imtable.gettable())
            del imtable
        return 0

    def makePSseries(self,lckeys,PSseriesfilename):
        print('### making epoch postage stamps...')
        if not(isinstance(lckeys,list)): lckeys = [lckeys,]
        #if not type(lckeys) is types.ListType: lckeys = [lckeys,]
        images = []

        for lckey in lckeys:
            fileval2match = self.canddifflc.getentry(lckey,self.canddifflc.cols_lc2filetable[0])
            print("fileval2match: ", fileval2match)
            filekey = self.candfile.filetable.search4entry(self.canddifflc.cols_lc2filetable[1],fileval2match)
            if filekey != None:
                images.extend([self.candfile.filetable.tmplfitsname(filekey),self.candfile.filetable.imfitsname(filekey),self.candfile.filetable.subfitsname(filekey)])
                #images.extend([self.candfile.filetable.subfitsname(filekey)])

        if images == []:
            tools.rmfile(PSseriesfilename)
            print('Warning: Could not find any diffims! skipping creation of PSseries')
            return 1
        print("IMAGES: ", images)
        MJDsub = getMJDsub4year(self.params.get_asint('A_YEAR'))
        tools.writeAllImages(PSseriesfilename, images, None, self.candfile.getentry(self.candkey,'RAaverage'), self.candfile.getentry(self.candkey,'DECaverage'), nX=3,MJDbase=MJDsub)
        print('postage stamps %s created ...' % PSseriesfilename)
        return 0

    def addepochPSseries2eventpage(self,eventwebpage,placeholder,width=None,height=None):
        if 'PSseries' in self.features:
            self.candfile.filetable.configcols(['photcode'],'x','0x%08x')
            photcodes= self.candfile.filetable.col_as_list('photcode')
            photcodes = tools.unique([(tools.hex2int(x) & self.candfile.params.get_ashex('FLAG_PHOTCODE_PURE')) for x in photcodes])
            if self.params.get('A_PSSERIES_PHOTCODES')!='':
                photcodes2use = self.params.gethexlist('A_PSSERIES_PHOTCODES')
                photcodes = tools.AandB(photcodes,photcodes2use)

            redo=0
            for photcode in photcodes:
                if not os.path.isfile(self.PSseriesfig(photcode)):
                    redo = 1
                    break


            # only use the keys from current year
            #MJDrange = gen.getMJDrange4year(self.year)
            #keys  = self.canddifflc.selectlckeys(MJDmin=MJDrange[0],MJDmax=MJDrange[1])
            ## MEH HACK not always the case! all MJD
            #MJDrange = gen.getMJDrange4year(self.year)
            #keys  = self.canddifflc.selectlckeys(MJDmin=MJDrange[0],MJDmax=MJDrange[1])
            #keys  = self.canddifflc.selectlckeys(MJDmin=0.0,MJDmax=MJDrange[1])
            keys  = self.canddifflc.selectlckeys()

            # get the high S/N keys and the last key
            highSNkeys = self.canddifflc.gethighSNkeys(skipforced=1,keys = keys)
            lastkeys = self.canddifflc.getlastkeys(skipforced=0,keys = keys)

            imtable=dumbhtmltable(1,border=0,cellspacing=0,cellpadding=0)
            # loop through the photcodes
            for photcode in photcodes:
                if photcode == 0:
                    continue
                # recursive placeholder!
                PSseries_fig = self.PSseriesfig(photcode)
                if redo:
                    if (not os.path.isfile(PSseries_fig)):
                        print('### Creating epoch of postage stamps:',PSseries_fig)
                        tools.rmfile(PSseries_fig)
                        if photcode in highSNkeys:
                        #if highSNkeys.has_key(photcode):
                            lckey = highSNkeys[photcode]['key']
                        elif photcode in lastkeys:
                        #elif lastkeys.has_key(photcode):
                            lckey = lastkeys[photcode]['key']
                        else:
                            print('No images for photcode 0x%x, thus skipping PSseries!' % photcode)
                            continue
                        errorflag = self.makePSseries(lckey,PSseries_fig)
                        if errorflag:
                            print('ERROR: something went wrong with the epoch series %s!' % (PSseries_fig))
                            tools.rmfile(PSseries_fig)
                            eventwebpage.substituteplaceholder(placeholder,'error: something went wrong while creating the epoch series!')
                            return 1
                imtable.startrow()
                imtable.addcol(imagestring4web(self.PSseriesfig(photcode),width=width,height=height),textalign='left')
                imtable.endrow()

            #imagestring = ''
            #for photcode in photcodes:
            #    imagestring += imagestring4web(self.PSseriesfig(photcode),width=width,height=height)
            eventwebpage.substituteplaceholder(placeholder,imtable.gettable())
            del imtable




    def PSseriesfig(self,photcode=None):
        name = os.path.join(self.fielddir, self.shortname+'_cand'+str(self.id))
        if photcode != None:
            try:
                name = name + '.%s' % (defs.photcode2filters[photcode])
            except:
                raise RuntimeError('Could not get filtername for photcode 0x%x, update photcode2filters in alerts.py!' % (photcode))
#        name = name + '.3PS.gif'
        name = name + '.3PS.jpg'
        return(name)

    def PSallfig(self,photcode=None):
        name = os.path.join(self.fielddir, self.shortname+'_cand'+str(self.id))
        if photcode != None:
            try:
                name = name + '.%s' % (defs.photcode2filters[photcode])
            except:
                raise RuntimeError('Could not get filtername for photcode 0x%x, update photcode2filters in alerts.py!' % (photcode))
#        name = name + '.PSall.gif'
        name = name + '.PSall.jpg'
        return(name)

    def PShighSNfig(self,photcode=None):
        name = os.path.join(self.fielddir, self.shortname+'_cand'+str(self.id))
        if photcode != None:
            try:
                name = name + '.%s' % (defs.photcode2filters[photcode])
            except:
                raise RuntimeError('Could not get filtername for photcode 0x%x, update photcode2filters in alerts.py!' % (photcode))
#        name = name + '.PShighSN.gif'
        name = name + '.PShighSN.jpg'
        return(name)

    def PSlastfig(self,photcode=None):
        name = os.path.join(self.fielddir, self.shortname+'_cand'+str(self.id))
        if photcode != None:
            try:
                name = name + '.%s' % (defs.photcode2filters[photcode])
            except:
                raise RuntimeError('Could not get filtername for photcode 0x%x, update photcode2filters in alerts.py!' % (photcode))
#        name = name + '.PSlast.gif'
        name = name + '.PSlast.jpg'
        return(name)

    def addepochPSseries2eventpage_highSN(self,webpage,placeholder,PSseries_fig,width=None,height=None):
        if 'PSseries' in self.features:
            tools.rmfile(PSseries_fig)
            highSNkeys = self.canddifflc.gethighSNkeys(skipforced=1)
            if 0 in highSNkeys:
            #if highSNkeys.has_key(0):
                lckey = highSNkeys[0]['key']
                errorflag = self.makePSseries(lckey,PSseries_fig)
                if errorflag:
                    print('ERROR: something went wrong with the epoch series %s!' % (PSseries_fig))
                    tools.rmfile(PSseries_fig)
                    webpage.substituteplaceholder(placeholder,'error: something went wrong while creating the epoch series!')
                    return 1
            else:
                webpage.substituteplaceholder(placeholder,'')

            self.addimage2webpage(webpage,PSseries_fig,placeholder,width=width,height=height)
        else:
            webpage.substituteplaceholder(placeholder,'')

    def addxyplot2eventpage(self, webpage, placeholder, xyplot, width=None,height=None):
        if 'xyplotsmall' in self.features:
            tools.rmfile(xyplot)
            matplot.makexyplot(self.canddifflc, self.candreglc, xyplot)
            self.addimage2webpage(webpage, xyplot, placeholder, width, height)
        else:
            webpage.substituteplaceholder(placeholder,'')

    def addalerttableinfo2eventpage(self,webpage,placeholder):
        if self.candfile.colexist('alerttable'):
            statusstring = ','.join(self.transmask.mask2type(self.candfile.getentry(self.candkey,'alerttable')))
            if statusstring != '':
                webpage.substituteplaceholder(placeholder,self.candfile.getentry(self.candkey,'designation')+'('+statusstring+')')
                return 0
        webpage.substituteplaceholder(placeholder,'')


    def addinfo2eventpage(self,webpage,placeholder):
        infotable=dumbhtmltable(6,border=1,cellspacing=0,cellpadding=2)

        colnames = {'RAaverage':'RA','DECaverage':'Dec'}
        for col in ['ID','RAaverage','DECaverage']:
            infotable.startrow()
            if col in colnames:
            #if colnames.has_key(col):
                colname = colnames[col]
            else:
                colname = col
            infotable.addcol(colname,textalign='left')
            infotable.addcol(self.candfile.colvalue2string(self.candkey,col),textalign='left')
            infotable.endrow()

        # for each photcode, magnitude and MJD of it
        # and delta r from host
        lastdiff = self.canddifflc.getlastkeys(skipforced=0)
        regobs   = self.candreglc.getkeys4photcodes(skipforced=1)

        for photcode in lastdiff.keys():
            if photcode == 0:
                continue
            pbname   = f2name(photcode)
            diffkey  = lastdiff[photcode]['key']
            diffdate = float(lastdiff[photcode]['MJD'])
            mag      = self.canddifflc.asfloat(diffkey, defs.lc_Mcol, default = 0.0)
            dmag     = self.canddifflc.asfloat(diffkey, defs.lc_dMcol, default = 0.0)
            zpt      = self.canddifflc.asfloat(diffkey, defs.lc_ZPTcol, default = 0.0)

            #infotable.startrow()
            #infotable.addcol('%s mag (%f)' % (pbname, diffdate), textalign='left',width='50%')
            #infotable.addcol('%.2f +/- %.2f' % (mag+zpt, dmag),  textalign='left',width='50%')
            #infotable.endrow()

            if photcode in regobs.keys():
                regkey = None
                dist   = 1e10
                for key in regobs[photcode]:
                    cdist = float(self.candreglc.getentry(key, 'deltaR'))
                    if cdist < dist:
                        dist   = cdist
                        regkey = key
                if regkey == None:
                    continue

                type    = self.candreglc.getentry(regkey, 'type')
                type    = type & 0xf
                if (type == 0x2):
                    tstr = 'Galaxy'
                elif (type == 0x1):
                    tstr = 'Star'
                elif (type == 0x3):
                    tstr = 'Double star'
                elif (type == 0x7):
                    tstr = 'Faint star'
                else:
                    tstr = 'Crap'

                infotable.startrow()
                infotable.addcol('%s offset' % (pbname), textalign='left')
                pscale = float(self.params.get('SW_PLATESCALE'))
                infotable.addcol('%.2f" (%s)' % (dist*pscale, tstr),  textalign='left')
                infotable.endrow()

        infotable.startrow()
        infotable.addcol('field',textalign='left')
        infotable.addcol(self.field,textalign='left')
        infotable.endrow()
        infotable.startrow()
        infotable.addcol('CCD#',textalign='left')
        infotable.addcol('%s' % self.amp,textalign='left')
        infotable.endrow()
        infotable.startrow()
        infotable.addcol('YSE-PZ name',textalign='left')
        infotable.addcol(self.candfile.colvalue2string(self.candkey,'ysename'),textalign='left')
        infotable.endrow()


        colnames = {'dist2veto_asec':'dist2K2'}
        """
        for col in ['K2ID','K2RA','K2DEC','K2m','dist2veto_asec']:
            infotable.startrow()
            if col in colnames:
            #if colnames.has_key(col):
                colname = colnames[col]
            else:
                colname = col
            infotable.addcol(colname,textalign='left')
            infotable.addcol(self.candfile.colvalue2string(self.candkey,col),textalign='left')
            infotable.endrow()
        """

        webpage.substituteplaceholder(placeholder,infotable.gettable())

    def add2buttons2eventpage(self, webpage, placeholder):
        if 'classifybuttons' in self.features:
            buttlines = []
            buttpage = webpageclass()
            buttpage.loaddefaultpage(self.params.get('WS_DEFAULTBUTTPAGE'),'STARTHERE','ENDHERE')
            buttpage.substituteplaceholder('SNIFFSCRIPT_PLACEHOLDER',self.params.get('WS_CGIACTIONS'))
            buttpage.substituteplaceholder('CLASSNAME_PLACEHOLDER', self.candfile.filename)
            buttpage.substituteplaceholder('CLASSREDIRECT_PLACEHOLDER', self.candidatelink())

            webpage.substituteplaceholder(placeholder, buttpage.lines)
        else:
            webpage.substituteplaceholder(placeholder, '')

    def addbuttons2eventpage(self, webpage, placeholder):
        if 'classifybuttons' in self.features:
            buttlines = []
            buttpage = webpageclass()
            buttpage.loaddefaultpage(self.params.get('WS_DEFAULTBUTTPAGE'),'STARTHERE','ENDHERE')
            buttpage.substituteplaceholder('SNIFFSCRIPT_PLACEHOLDER',self.params.get('WS_CGIACTIONS'))
            buttpage.substituteplaceholder('CLASSNAME_PLACEHOLDER', self.candfile.filename)
            buttpage.substituteplaceholder('CLASSREDIRECT_PLACEHOLDER', self.candidatelink())

            buttpage.substituteplaceholder('CMDDIR_PLACEHOLDER', self.cmddir)
            buttpage.substituteplaceholder('CAND_PLACEHOLDER', str(self.id))

            radecstring = 'RA=%s&Dec=%s' % (self.candfile.getentry(self.candkey, 'RAaverage'),self.candfile.getentry(self.candkey, 'DECaverage'))
            link = 'http://store.anu.edu.au:3001/cgi-bin/lc.pl?'+ radecstring +'&Radius=5&Equinox=J2000&Units=HMS%2fDMS%2farcsec&Star_Count=10&Action=Submit'
            buttpage.substituteplaceholder('MACHO_PLACEHOLDER', addlink2string('Search MACHO',link))

            # next
            if self.index == len(self.candkeys)-1:
                buttpage.substituteplaceholder('CLASSREDIRECTN_PLACEHOLDER', '%s' % self.candidatelink())
            else:
                nextkey = self.candkeys[self.index+1]
                buttpage.substituteplaceholder('CLASSREDIRECTN_PLACEHOLDER', '%s#%d' % (self.htmladdress(), self.candfile.getentry(nextkey,'ID')))

            # prev
            if self.index == 0:
                buttpage.substituteplaceholder('CLASSREDIRECTP_PLACEHOLDER', '%s' % self.candidatelink())
            else:
                prevkey = self.candkeys[self.index-1]
                buttpage.substituteplaceholder('CLASSREDIRECTP_PLACEHOLDER', '%s#%d' % (self.htmladdress(), self.candfile.getentry(prevkey,'ID')))

            webpage.substituteplaceholder(placeholder, buttpage.lines)
        else:
            webpage.substituteplaceholder(placeholder, '')

    def addsdsslink2eventpage(self,webpage,placeholder):
        rastr = self.candfile.colvalue2string(self.candkey,'RAaverage')
        decstr = self.candfile.colvalue2string(self.candkey,'DECaverage')
#        link = 'http://cas.sdss.org/dr7/en/tools/explore/obj.asp?ra='+rastr+'&dec='+decstr
#  RC - changed 20121010 to point to dr9
#        link = 'http://skyserver.sdss3.org/dr9/en/tools/explore/obj.asp?ra='+rastr+'&dec='+decstr
#  RC - changed 20131015 to point to dr10
        link = 'http://skyserver.sdss3.org/dr10/en/tools/explore/obj.aspx?ra='+rastr+'&dec='+decstr
        linkstring = addlink2string('SDSS link',link)
        webpage.substituteplaceholder(placeholder,linkstring)



class websnifflevels(websniffclass):
    def __init__(self, candfile, field=None, amp=None, diffdate=None, MJD=None, short=0, skipcheckintegrity=0, skipcorrectfluxes=False, skipinit=False):
        websniffclass.__init__(self)
        self.initparams()

        if MJD == None:
            self.year = self.params.get_asint('A_YEAR')
        else:
            self.year = gen.getyear4MJD(float(MJD))
            self.MJD = float(MJD)

        # if there is a placeholder <year> in WS_DIR or WS_HTMLADDRESS, sub it!
        if re.search('\<yyyy\>',self.params.get('WS_DIR')):
            newWS_DIR = re.sub('\<yyyy\>','%d' % gen.getYYYY4year(self.year),self.params.get('WS_DIR'))
            self.params.set('WS_DIR',newWS_DIR)
        if re.search('\<yyyy\>',self.params.get('WS_HTMLADDRESS')):
            newWS_HTMLADDRESS = re.sub('\<yyyy\>','%d' % gen.getYYYY4year(self.year),self.params.get('WS_HTMLADDRESS'))
            self.params.set('WS_HTMLADDRESS',newWS_HTMLADDRESS)

        self.short = short
        if self.short or skipinit:
            # quick and dirty
            self.candfile = pipeclasses.lclistclass()
            self.candfile.filename = candfile
        else:
            try:
                self.initcandfile(candfile, skipcheckintegrity=skipcheckintegrity,skipcorrectfluxes=skipcorrectfluxes)
            except Exception as E:
                print('CANNOT READ %s OR ITS CONTENTS :\n%s' % (candfile, E))
                sys.exit(1)

        self.shortname = os.path.basename(re.sub('\.'+self.params.get('DIFFCLUSTERSSUFFIX'),'',self.candfile.filename))

        # Hack for YSE: remove the double <field>_<amp>
        self.shortname = re.sub('^[a-zA-Z0-9_]+\.','',self.shortname)
        if field == None and amp == None and diffdate == None:
            self.field = self.shortname[:4]

            path, self.filename = os.path.split(self.candfile.filename)
            if path == '':
                prin( 'MUST USE ABSOLUTE PATHS')
                sys.exit(1)

            path, self.amp      = os.path.split(path)
            path, self.diffdate = os.path.split(path)
        else:
            self.field    = field
            self.amp      = amp

            # HACK FOR NOW...  armin sends date/amp

            #self.diffdate = diffdate
            dd, da = os.path.split(diffdate)
            assert da == amp
            self.diffdate = dd

        self.ctime    = time.ctime()
        self.features = self.params.get('WS_FEATURES').split(',')


    def check4veto(self):
        passed       = []
        vetomask = vetomask_alerttable = 0
        if self.params.get('WS_VETOMASK') != None:
            vetomask = self.transmask.type2mask(self.params.get('WS_VETOMASK'))
        if self.params.get('WS_VETOMASK_ALERTTABLE') != None: vetomask_alerttable = self.transmask.type2mask(string.split(self.params.get('WS_VETOMASK_ALERTTABLE'),','))
        vetobadfits = self.params.get('WS_VETO_BAD_FITS')
        if vetobadfits and self.candfile.colexist('fitcut'):
            self.candfile.configcols(['fitcut'],'x','0x%08x')
        self.candfile.configcols(['pass'],'d')
        for candkey in self.candfile.rowkeys():
            if self.candfile.getentry(candkey,'class') & vetomask:
                print('Skipping ID %d because class & WS_VETOMASK' % (self.candfile.getentry(candkey,'ID')))
                continue
            if self.candfile.colexist('alerttable'):
                if self.candfile.getentry(candkey,'alerttable') & vetomask_alerttable:
                    print('Skipping ID %d because event is already in alerts table' % (self.candfile.getentry(candkey,'ID')))
                    continue
            passed.append(candkey)
        return passed


    def makelevels(self, keys2show=None,skip_YSEobjects_without_detections=True):
        self.passkeys = self.check4veto()
        # if nothing passes veto, don't make it!
        if keys2show: #Overrides any veto checking
            self.passkeys = keys2show

        if len(self.passkeys) == 0:
            return

        if not os.path.isdir(self.params.get('WS_DIR')):
            os.makedirs(self.params.get('WS_DIR'))

        self.cmddir  = os.path.join(self.params.get('WS_DIR'), 'cmds')
        if not os.path.isdir(self.cmddir):
            os.makedirs(self.cmddir)

        self.diffdatedir  = os.path.join(self.params.get('WS_DIR'), self.diffdate)
        if not os.path.isdir(self.diffdatedir):
            os.makedirs(self.diffdatedir)

        self.ampdir   = os.path.join(self.diffdatedir, self.amp)
        if not os.path.isdir(self.ampdir):
            os.mkdir(self.ampdir)

        self.fielddir = os.path.join(self.ampdir, self.shortname)
        if not os.path.isdir(self.fielddir):
            os.mkdir(self.fielddir)

        if not self.short:
            self.makecandpage(self.passkeys,skip_YSEobjects_without_detections=skip_YSEobjects_without_detections)

        self.makedatepage()
        self.makeamppage()
        self.makefieldpage()

    def makedatepage(self):
        ddatepage = os.path.join(self.params.get('WS_DIR'), self.params.get('WS_DATEPAGENAME'))

        ddatelines = []
        twocolpage = webpageclass()
        twocolpage.loaddefaultpage(self.params.get('WS_DEFAULT2COLPAGE2'),'STARTHERE','ENDHERE')
        for file in os.listdir(self.params.get('WS_DIR')):
            # skip this one!
            if file == 'cmds':
                continue

            fdir = os.path.join(self.params.get('WS_DIR'), file)
            if os.path.isdir(fdir):
                mtime = os.stat(fdir)[stat.ST_MTIME]

                tempwebpage = copy.deepcopy(twocolpage)
                tempwebpage.substituteplaceholder('COL1_PLACEHOLDER', file)
                tempwebpage.substituteplaceholder('COL2_PLACEHOLDER', time.ctime(mtime))
                ddatelines.extend(tempwebpage.lines)

        websniffpage = webpageclass()
        websniffpage.loaddefaultpage(self.params.get('WS_DEFAULTDATEPAGE'))
        websniffpage.substituteplaceholder('DATES_PLACEHOLDER', ddatelines)
        websniffpage.substituteplaceholder('LASTUPDATE_PLACEHOLDER', self.ctime)
        websniffpage.savepage(ddatepage)

    def makeamppage(self):
        amppage = os.path.join(self.diffdatedir, self.params.get('WS_AMPPAGENAME'))

        amplines = []
        twocolpage = webpageclass()
        twocolpage.loaddefaultpage(self.params.get('WS_DEFAULT2COLPAGE2'),'STARTHERE','ENDHERE')
        for file in os.listdir(self.diffdatedir):
            fdir = os.path.join(self.diffdatedir, file)
            if os.path.isdir(fdir):

                mtime = os.stat(fdir)[stat.ST_MTIME]

                tempwebpage = copy.deepcopy(twocolpage)
                tempwebpage.substituteplaceholder('COL1_PLACEHOLDER', file)
                tempwebpage.substituteplaceholder('COL2_PLACEHOLDER', time.ctime(mtime))
                amplines.extend(tempwebpage.lines)

        websniffpage = webpageclass()
        websniffpage.loaddefaultpage(self.params.get('WS_DEFAULTAMPPAGE'))
        websniffpage.substituteplaceholder('AMPS_PLACEHOLDER', amplines)
        websniffpage.substituteplaceholder('GOBACK_PLACEHOLDER', '../'+self.params.get('WS_DATEPAGENAME'))
        websniffpage.substituteplaceholder('LASTUPDATE_PLACEHOLDER', self.ctime)
        websniffpage.savepage(amppage)

    def makefieldpage(self):
        # this one has buttons!
        fieldpage = os.path.join(self.ampdir, self.params.get('WS_FIELDPAGENAME'))

        fieldlines   = []
        fieldcolpage = webpageclass()
        fieldcolpage.loaddefaultpage(self.params.get('WS_DEFAULTFIELDCOLPAGE'),'STARTHERE','ENDHERE')

        for file in os.listdir(self.ampdir):
            fdir = os.path.join(self.ampdir, file)
            if os.path.isdir(fdir):
                tempwebpage = copy.deepcopy(fieldcolpage)
                tempwebpage.substituteplaceholder('CAND_PLACEHOLDER', file)

                snifflog = fdir+'.slog'
                if not os.path.isfile(snifflog):
                    open(snifflog, 'w').close()

                sniffdir = '%s/%s/%s/%s/%s.html' % (self.params.get('WS_HTMLADDRESS'),self.diffdate,self.amp,file,file)
                if re.search('^file:',self.params.get('WS_HTMLADDRESS')):
                    pass
                else:
                    sniffdir = 'http://%s' % sniffdir

                tempwebpage.substituteplaceholder('SNIFFLOGROOT_PLACEHOLDER', os.path.basename(snifflog))
                tempwebpage.substituteplaceholder('SNIFFLOG_PLACEHOLDER', snifflog)
                tempwebpage.substituteplaceholder('SNIFFSCRIPT_PLACEHOLDER', self.params.get('WS_CGIACTIONS'))
                #tempwebpage.substituteplaceholder('FIELD_PLACEHOLDER', self.htmladdress())
                tempwebpage.substituteplaceholder('FIELD_PLACEHOLDER', sniffdir)
                tempwebpage.substituteplaceholder('CLASSNAME_PLACEHOLDER', self.candfile.filename)

                fieldlines.extend(tempwebpage.lines)

        websniffpage = webpageclass()
        websniffpage.loaddefaultpage(self.params.get('WS_DEFAULTFIELDPAGE'))
        websniffpage.substituteplaceholder('FIELDS_PLACEHOLDER', fieldlines)
        websniffpage.substituteplaceholder('GOBACK_PLACEHOLDER', '../')
        websniffpage.substituteplaceholder('LASTUPDATE_PLACEHOLDER', self.ctime)
        websniffpage.savepage(fieldpage)

    def makecandpage(self, candkeys=None,skip_YSEobjects_without_detections=True):
        websniffpage = webpageclass()
        websniffpage.loaddefaultpage(self.params.get('WS_DEFAULTCANDPAGE'))
        websniffpage.substituteplaceholder('FIELD_PLACEHOLDER',self.field)
        websniffpage.substituteplaceholder('AMP_PLACEHOLDER','%s' % self.amp)

        candlines = []
        candwebpage = webpageclass()
        candwebpage.loaddefaultpage(self.params.get('WS_DEFAULTCANDCOLPAGE'),'STARTHERE','ENDHERE')

        if candkeys == None:
            self.candkeys = self.candfile.rowkeys()
        else:
            self.candkeys = candkeys

        candkeyspassed = [] # this is only relevant if WS_VETO_BAD_FITS=1

        indeces = range(len(self.candkeys))

        #clusteroutfilename = os.path.join(self.fielddir,os.path.basename(self.candfile.filename))
        clusteroutfilename = f'{self.fielddir}.diff.clusters'
        print(f'SAVING CLUSTER FILE {clusteroutfilename}')
        pipeclasses.savelclist(self.candfile,clusteroutfilename)

        for index in indeces:
            
            self.index = index
            candkey    = self.candkeys[self.index]


            print('\n### %d %s %s %s' % (self.candfile.getentry(candkey,'ID'),
                                         self.candfile.getentry(candkey,'RAaverage'),
                                         self.candfile.getentry(candkey,'DECaverage'),
                                         time.strftime('%m/%d/%y: %H%M%S',time.gmtime())))
            #print '############################################################################################### HACK!!!!!!!!!!!!!!!!!!!!'
            #if int(self.candfile.getentry(candkey,'ID')) != 2367:
            #    continue

            self.initcand(candkey)
            tempcandwebpage = copy.deepcopy(candwebpage)

            # reset the offset
            self.applydifffluxoffset = 0
            self.difffluxoffset = None

            tempcandwebpage.substituteplaceholder('TARGET_PLACEHOLDER', '%s' % (self.id))
            tempcandwebpage.substituteplaceholder('REF_PLACEHOLDER','%s' % (self.candidatelink()))
            tempcandwebpage.substituteplaceholder('NAME_PLACEHOLDER','Field %s, Chop# %s, Candidate %d<br>%s' %
                                                  (self.field,self.amp,self.candfile.getentry(self.candkey,'ID'),self.candidatelink()))

            self.adddifflc2eventpage(tempcandwebpage, 'DIFFLC_FORCED_PLACEHOLDER', self.addsuffix4web('.difflc.forced.png'),title='FORCED diffim photometry',ylabel='forced diffim flux',onlyforced=1,onlynonforced=0,Nmaskmax=self.params.get('WS_NMASKMAX'),width=600,height=400)
            self.adddifflc2eventpage(tempcandwebpage, 'DIFFLC_UNFORCED_PLACEHOLDER', self.addsuffix4web('.difflc.unforced.png'),title='diffim photometry',onlyforced=0,onlynonforced=1,width=600,height=400)
            #self.adddifflcall2eventpage(tempcandwebpage, 'ALL_T_LC_PLACEHOLDER', self.addsuffix4web('.all_difflc.png'))

            self.adddatfile2eventpage(tempcandwebpage, 'DATFILE_LINK_PLACEHOLDER', self.addsuffix4web('.forced.difflc.txt'),self.addsuffix4web('.unforced.difflc.txt'))

            #self.addsdsslink2eventpage(tempcandwebpage, 'SDSSLINK_PLACEHOLDER')
            self.addmaglc2eventpage(tempcandwebpage, 'MAGLC_PLACEHOLDER', 'MAGLCLINK_PLACEHOLDER', self.addsuffix4web('.maglc.png'),onlyforced=1,onlynonforced=0,width=600,height=400)
            self.addepochPSseries2eventpage(tempcandwebpage,'EPOCHSERIES_PLACEHOLDER', '.PS.jpg')
            self.addxyplot2eventpage(tempcandwebpage, 'SMALLXYPLOT_PLACEHOLDER', self.addsuffix4web('.xy.png'))
            self.addPSall2eventpage(tempcandwebpage, 'ALLSUBS_PLACEHOLDER','ALLSUBSLINK_PLACEHOLDER')
            self.addPSlast2eventpage(tempcandwebpage, 'PSLAST_PLACEHOLDER')
            self.addPShighSN2eventpage(tempcandwebpage, 'PSHIGHSN_PLACEHOLDER')
            self.addalerttableinfo2eventpage(tempcandwebpage,'ALERTTABLEINFO_PLACEHOLDER')
            self.addinfo2eventpage(tempcandwebpage,'CANDINFO_PLACEHOLDER')
            #self.addbuttons2eventpage(tempcandwebpage, 'BUTTONS2x2_PLACEHOLDER')

            alertmask = tools.hex2int(self.candfile.getentry(candkey,'alert_YSE'))
            if skip_YSEobjects_without_detections and (alertmask & 0x80000000):
                print(f'Skipping candidate {self.candfile.getentry(candkey,"ID")} since it is a YSE object with no detections')
                continue

            candlines.extend(tempcandwebpage.lines)
            candkeyspassed.append(self.candkeys[self.index])
            #if index>1:
            #break

        if len(candkeyspassed)>0:
            print('Putting %d out of %d candidates into sniffpage %s!' % (len(candkeyspassed),len(self.candkeys),self.localaddress()))
            websniffpage.substituteplaceholder('CANDIDATES_PLACEHOLDER',candlines)
            #websniffpage.substituteplaceholder('REF_PLACEHOLDER', 'file://'+self.localaddress())
            websniffpage.substituteplaceholder('GOBACK_PLACEHOLDER', '../#'+self.shortname)
            websniffpage.substituteplaceholder('LASTUPDATE_PLACEHOLDER',self.ctime)
            websniffpage.savepage(self.localaddress())
        else:
            print('No candidate out of %d passed the cuts' % (len(self.candkeys)))
            files2delete =  glob.glob('%s/%s*' % (self.fielddir, self.shortname))
            files2delete.extend(glob.glob('%s/index.html' % (self.fielddir)))
            for file in files2delete:
                print('Removing %s' % file)
                os.remove(file)
            print('Removing %s' % self.fielddir)
            os.rmdir(self.fielddir)

        self.candkeys = candkeyspassed

    def localaddress(self):
        return '%s/index.html' % (self.fielddir)
    def htmladdress(self):
        #return '%s/%s/%s.html' % (self.params.get('WS_HTMLADDRESS'),self.diffdatedir,self.shortname)
        #return 'http://%s/%s/%s/%s/%s.html' % (self.params.get('WS_HTMLADDRESS'),self.diffdate,self.amp,self.shortname,self.shortname)
        return '%s/%s/%s/%s/index.html' % (self.params.get('WS_HTMLADDRESS'),self.diffdate,self.amp,self.shortname)
    def candidatelink(self):
        return '%s#%d' % (self.htmladdress(),self.id)

    def addsuffix4web(self, suffix):
        return os.path.join(self.fielddir, self.shortname+'_cand'+str(self.id)+suffix)

if __name__=='__main__':
    argv = sys.argv
    short = 0
    if '-short' in argv:
        short = 1
        argv.remove('-short')

    if len(argv) == 2:
        # requires parsing the absolute path of sys.argv[1]
        #    for info on field,amp,date
        websniff = websnifflevels(argv[1], short=short)
        if len(websniff.candfile.rowkeys()) > 0:
            websniff.makelevels()
    elif len(argv) == 6:
        field    = argv[2]
        amp      = argv[3]
        diffdate = argv[4]
        MJD      = argv[5]
        websniff = websnifflevels(argv[1], field, amp, diffdate, MJD, short=short)
        if len(websniff.candfile.rowkeys()) > 0:
            websniff.makelevels(skip_YSEobjects_without_detections=False)
    else:
        print('Somebody should provide a help string like:')
        print ('\twebsniff.py candfile field amp diffdate mjd')
        sys.exit(1)

    print('SUCCESS: websniff.py')


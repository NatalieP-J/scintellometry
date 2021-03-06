from __future__ import division

import numpy as np
from numpy.polynomial import Polynomial
# to compile fortran source, go to scintellometry/folding and run
# f2py --fcompiler=gfortran -m fortran_fold_gmrt -c fortran/fold_gmrt.f90
from fortran_fold_gmrt import fold
from pmap import pmap


if __name__ == '__main__':
    ipsr = 2
    psrname = ['0809+74','1508+55','1957+20','1919+21']
    dm0 = np.array([5.75130, 19.5990, 29.11680, 12.4309])
    # for may 17, 4AM
    p00 = np.array([1292.19138600024303/1000,
                    0.73969358444999955,
                    0.0016072823189784409,
                    1337.21932367595014])
    gates = np.zeros((4,4))
    gates[1] = [59,60,61,62]
    gates[2] = [1,8,9,16]
    gates[3] = [224,226,227,231]

    # Fiddle with DM of 1957
    dm0[2] *= 1.001
    # select pulsar
    psr = psrname[ipsr]
    dm = 0.
    polyco = np.array([0.89445372020383995,
                       37329.532088339118,
                       0.002514254791367953,
                       9.2233535227755351e-06,
                       -2.7654363721954842e-08])
    window = np.array([-60., 60.])  # range for which polyco is defined
    # polyco is for 00:30 UTC midtime, while obs starts at 23:47;
    # but get good fit to frequency at known sample rate at 23:50:08.849
    domain = (window-(43.+22/60.)+90.)*60.
    phasepol = Polynomial(polyco, domain, window)

    igate = None
    fndir1 = '/mnt/scratch-3week/pen/Pulsar/'

    file1 = fndir1 + psr + 'L.float'
    file2 = None

    nhead = 0*32*1024*1024
    # frequency samples in a block; every sample is two bytes: real, imag
    nblock = 512
    # nt=45 for 1508, 180 for 0809 and 156 for 0531
    nt = 26200  # number of sets to fold  -> //128 for quick try
    ntint = 1024*32*1024//(nblock*2)//4  # total # of blocks per set
    ngate = 32*4  # number of bins over the pulsar period
    ntbin = 16*2  # number of bins the time series is folded in
    ntw = min(128*2*100, nt*ntint)  # number of samples for waterfall

    # samplerate = 100.e6/3. * 2 * (1.+2./16/622.156270897/1100)
    # from /mnt/raid-project/gmrt/pen/B1937/read_float.f90
    # phasepol = Polynomial([0.,1./(1.60731438719155/1000*(1-4*3.252e-07))])
    samplerate = 33333333.*2

    fbottom = 306.   # MHz
    fband = 2*16.6666666  # MHz

    verbose = True
    do_foldspec = True
    do_waterfall = False
    foldspec2, waterfall = fold(file1, file2, 'f4', samplerate,
                                fbottom, fband, nblock, nt, ntint,
                                nhead, ngate, ntbin, ntw,
                                dm, phasepol.coef, half_data_bug=True,
                                paired_samples_bug=False,
                                do_foldspec=do_foldspec,
                                do_waterfall=do_waterfall,
                                verbose=verbose, progress_interval=10)
    if do_foldspec:
        np.save('foldspec2'+psr, foldspec2)
    if do_waterfall:
        np.save('waterfall'+psr, waterfall)
    foldspec1 = foldspec2.sum(axis=2)
    fluxes = foldspec1.sum(axis=0)
    foldspec3 = foldspec2.sum(axis=0)
    if igate is not None:
        dynspect = foldspec2[:,igate[0]-1:igate[1],:].sum(axis=1)
        dynspect2 = foldspec2[:,igate[2]-1:igate[3],:].sum(axis=1)
        f = open('dynspect'+psr+'.bin', 'wb')
        f.write(dynspect.T.tostring())
        f.write(dynspect2.T.tostring())
        f.close()
    f = open('flux.dat', 'w')
    for i, flux in enumerate(fluxes):
        f.write('{0:12d} {1:12.9g}\n'.format(i+1, flux))
    f.close()
    plots = True
    if plots:
        # pmap('waterfall.pgm', waterfall, 1, verbose=True)
        pmap('folded'+psr+'.pgm', foldspec1, 0, verbose)
        pmap('foldedbin'+psr+'.pgm', foldspec2.reshape(nblock,-1), 1, verbose)
        pmap('folded3'+psr+'.pgm', foldspec3, 0, verbose)
        if igate is not None:
            dall = dynspect+dynspect2
            dall_sum0 = dall.sum(axis=0)
            dall_sum0 = np.where(dall_sum0, dall_sum0, 1.)
            dall = dall/(dall_sum0/nblock)
            dall[0,:] = 0
            pmap('dynspect'+psr+'.pgm', dall, 0, verbose)
            t1 = dynspect/(dynspect.sum(axis=0)/nblock)
            t2 = dynspect2/(dynspect2.sum(axis=0)/nblock)
            dsub = t1-t2
            dsub[0,:] = 0
            pmap('dynspectdiff'+psr+'.pgm', dsub, 0, verbose)

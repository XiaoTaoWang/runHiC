# Created on Tue Dec 23 21:15:19 2014

# Author: XiaoTao Wang
# Organization: HuaZhong Agricultural University

import logging, os, subprocess, time, gc
import numpy as np
from mirnylib.h5dict import h5dict

log = logging.getLogger(__name__)

def sleep():
    
    for _ in range(3):
        time.sleep(0.1)
    gc.collect()
    for _ in range(3):
        time.sleep(0.1)

def cleanFile(filename):
    if os.path.exists(filename):
        os.remove(filename)
    
def cleanDirectory(dirName):
    for i in os.listdir(dirName):
        os.remove(os.path.join(dirName, i))

def fetchChromsizes(genomeFolder, genomeName):

    chromsizes = []
    pread = subprocess.Popen(['fetchChromSizes', genomeName], stdout=subprocess.PIPE)
    inStream = pread.stdout
    for line in inStream:
        parse = line.decode().rstrip().split()
        c, s = parse[0], parse[1]
        chromsizes.append((c, s))
    chromsizes.sort()
    pread.communicate()

    outfile = os.path.join(genomeFolder, '.'.join([genomeName, 'chrom', 'sizes']))
    with open(outfile, 'w') as out:
        for line in chromsizes:
            out.write('\t'.join(line)+'\n')
    
    return outfile
    
# Convert Matrix to Scipy Sparse Matrix
def toSparse(source, csr = False):
    """
    Convert intra-chromosomal contact matrices to sparse ones.
    
    Parameters
    ----------
    source : str
         Hdf5 file name.
    
    idx2label : dict
        A dictionary for conversion between zero-based indices and
        string chromosome labels.
    
    csr : bool
        Whether to use CSR (Compressed Row Storage) format or not.
    
    """
    import zipfile, tempfile
    from numpy.lib.format import write_array
    from scipy import sparse
    
    lib = h5dict(source, mode = 'r')
    
    ## Uniform numpy-structured-array format
    itype = np.dtype({'names':['bin1', 'bin2', 'IF'],
                          'formats':[np.int, np.int, np.float]})
    
    ## Create a Zip file in NPZ case
    if not csr:
        output = source.replace('.hm', '-sparse.npz')
    else:
        output = source.replace('.hm', '-csrsparse.npz')
    
    Zip = zipfile.ZipFile(output, mode = 'w', allowZip64 = True)
    fd, tmpfile = tempfile.mkstemp(suffix = '-numpy.npy')
    os.close(fd)
    
    log.log(21, 'Sparse Matrices will be saved to %s', output)
    log.log(21, 'Only intra-chromosomal matrices will be taken into account')
    log.log(21, 'Coverting ...')
    
    count = 0
    
    for i in lib:
        if (i != 'resolution') and (i != 'genomeInformation') and (len(set(i.split())) == 1):
            # Used for the dict-like key
            key = lib['genomeInformation']['idx2label'][int(i.split()[0])]
            
            log.log(21, 'Chromosome %s ...', key)
            # 2D-Matrix
            H = lib[i]
            
            if not csr:
                # Triangle Array
                Triu = np.triu(H)
                # Sparse Matrix in Memory
                x, y = np.nonzero(Triu)
                values = Triu[x, y]
                temp = np.zeros(values.size, dtype = itype)
                temp['bin1'] = x
                temp['bin2'] = y
                temp['IF'] = values
            else:
                temp = sparse.triu(H, format = 'csr')
            
            fname = key + '.npy'
            fid = open(tmpfile, 'wb')
            try:
                write_array(fid, np.asanyarray(temp))
                fid.close()
                fid = None
                Zip.write(tmpfile, arcname = fname)
            finally:
                if fid:
                    fid.close()
                    
            log.log(21, 'Done!')
            
            count += 1
    
    if count == 0:
        log.warning('Empty source file!')
            
    # Other information
    for i in ['resolution', 'genomeInformation']:
        fname = '.'.join([i, 'npy'])
        fid = open(tmpfile, 'wb')
        try:
            write_array(fid, np.asanyarray(lib[i]))
            fid.close()
            fid = None
            Zip.write(tmpfile, arcname = fname)
        finally:
            if fid:
                fid.close()
    
    os.remove(tmpfile)
    
    Zip.close()
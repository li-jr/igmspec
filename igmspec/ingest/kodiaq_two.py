""" Module to ingest KODIAQ DR2 Survey data

O'Meara et al. 2017
"""
from __future__ import print_function, absolute_import, division, unicode_literals


import numpy as np
import pdb
import os, json

import datetime

from astropy.table import Table, Column
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astropy import units as u
from astropy.io import fits

from linetools import utils as ltu
from linetools.spectra import io as lsio

from specdb.build.utils import chk_meta
from specdb.build.utils import set_resolution
from specdb.build.utils import init_data



def grab_meta():
    """ Grab KODIAQ meta Table
    Returns
    -------

    """
    kodiaq_file = os.getenv('RAW_IGMSPEC')+'/KODIAQ2/KODIAQ_DR2_summary.ascii'
    kodiaq_meta = Table.read(kodiaq_file, format='ascii', comment='#')
    # Verify DR1
    dr2 = kodiaq_meta['kodrelease'] == 2
    kodiaq_meta = kodiaq_meta[dr2]
    # RA/DEC, DATE
    ra = []
    dec = []
    dateobs = []
    for row in kodiaq_meta:
        # Fix DEC
        # Get RA/DEC
        coord = ltu.radec_to_coord((row['sRA'],row['sDEC']))
        ra.append(coord.ra.value)
        dec.append(coord.dec.value)
        # DATE
        dvals = row['pi_date'].split('_')
        tymd = str('{:s}-{:s}-{:02d}'.format(dvals[-1],dvals[1][0:3],int(dvals[2])))
        tval = datetime.datetime.strptime(tymd, '%Y-%b-%d')
        dateobs.append(datetime.datetime.strftime(tval,'%Y-%m-%d'))
    kodiaq_meta.add_column(Column(ra, name='RA_GROUP'))
    kodiaq_meta.add_column(Column(dec, name='DEC_GROUP'))
    kodiaq_meta.add_column(Column(dateobs, name='DATE-OBS'))
    #
    kodiaq_meta['INSTR'] = 'HIRES'
    kodiaq_meta['TELESCOPE'] = 'Keck-I'
    kodiaq_meta['STYPE'] = str('QSO')
    # z
    kodiaq_meta.rename_column('zem', 'zem_GROUP')
    kodiaq_meta['sig_zem'] = 0.
    kodiaq_meta['flag_zem'] = str('SDSS-SIMBAD')
    #
    assert chk_meta(kodiaq_meta, chk_cat_only=True)
    return kodiaq_meta


def hdf5_adddata(hdf, sname, meta, debug=False, chk_meta_only=False):
    """ Append KODIAQ data to the h5 file

    Parameters
    ----------
    hdf : hdf5 pointer
    IDs : ndarray
      int array of IGM_ID values in mainDB
    sname : str
      Survey name
    chk_meta_only : bool, optional
      Only check meta file;  will not write

    Returns
    -------

    """
    # Add Survey
    print("Adding {:s} survey to DB".format(sname))
    kodiaq_grp = hdf.create_group(sname)
    # Load up
    # Checks
    if sname != 'KODIAQ_DR2':
        raise IOError("Not expecting this survey..")

    # Build spectra (and parse for meta)
    nspec = len(meta)
    max_npix = 60000  # Just needs to be large enough
    # Init
    data = init_data(max_npix, include_co=False)
    spec_set = hdf[sname].create_dataset('spec', data=data, chunks=True,
                                         maxshape=(None,), compression='gzip')
    spec_set.resize((nspec,))
    # Lists
    Rlist = []
    wvminlist = []
    wvmaxlist = []
    gratinglist = []
    npixlist = []
    speclist = []
    # Loop
    path = os.getenv('RAW_IGMSPEC')+'/KODIAQ2/Data/'
    maxpix = 0
    for jj,row in enumerate(meta):
        # Generate full file
        full_file = path+row['qso']+'/'+row['pi_date']+'/'+row['spec_prefix']+'_f.fits'
        # Extract
        print("KODIAQ: Reading {:s}".format(full_file))
        hduf = fits.open(full_file)
        head = hduf[0].header
        spec = lsio.readspec(full_file)
        # Parse name
        fname = full_file.split('/')[-1]
        # npix
        npix = spec.npix
        if npix > max_npix:
            raise ValueError("Not enough pixels in the data... ({:d})".format(npix))
        else:
            maxpix = max(npix,maxpix)
        # Some fiddling about
        for key in ['wave','flux','sig']:
            data[key] = 0.  # Important to init (for compression too)
        data['flux'][0][:npix] = spec.flux.value
        data['sig'][0][:npix] = spec.sig.value
        data['wave'][0][:npix] = spec.wavelength.value
        # Meta
        speclist.append(str(fname))
        wvminlist.append(np.min(data['wave'][0][:npix]))
        wvmaxlist.append(np.max(data['wave'][0][:npix]))
        if 'XDISPERS' in head.keys():
            if head['XDISPERS'].strip() == 'UV':
                gratinglist.append('BLUE')
            else:
                gratinglist.append('RED')
        else:  # Original, earl data
            gratinglist.append('RED')
        npixlist.append(npix)
        try:
            Rlist.append(set_resolution(head))
        except ValueError:
            pdb.set_trace()
        # Only way to set the dataset correctly
        if chk_meta_only:
            continue
        spec_set[jj] = data

    #
    print("Max pix = {:d}".format(maxpix))
    # Add columns
    meta.add_column(Column([2000.]*nspec, name='EPOCH'))
    meta.add_column(Column(speclist, name='SPEC_FILE'))
    meta.add_column(Column(npixlist, name='NPIX'))
    meta.add_column(Column(wvminlist, name='WV_MIN'))
    meta.add_column(Column(wvmaxlist, name='WV_MAX'))
    meta.add_column(Column(Rlist, name='R'))
    meta.add_column(Column(gratinglist, name='DISPERSER'))
    meta.add_column(Column(np.arange(nspec,dtype=int),name='GROUP_ID'))

    # Add HDLLS meta to hdf5
    if chk_meta(meta):
        if chk_meta_only:
            pdb.set_trace()
        hdf[sname]['meta'] = meta
    else:
        raise ValueError("meta file failed")
    # References
    refs = [dict(url='http://adsabs.harvard.edu/abs/2017AJ....154..114O',
                 bib='kodiaq')
            ]
    jrefs = ltu.jsonify(refs)
    hdf[sname]['meta'].attrs['Refs'] = json.dumps(jrefs)
    #
    return


def add_ssa(hdf, dset):
    """  Add SSA info to meta dataset
    Parameters
    ----------
    hdf
    dset : str
    """
    from specdb.ssa import default_fields
    Title = '{:s}: Keck/HIRES KODIAQ DR1'.format(dset)
    ssa_dict = default_fields(Title, flux='normalized')
    hdf[dset]['meta'].attrs['SSA'] = json.dumps(ltu.jsonify(ssa_dict))

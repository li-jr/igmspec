""" Module to build the hdf5 database file for IGMspec
"""
from __future__ import print_function, absolute_import, division, unicode_literals

import numpy as np
import os, warnings

import h5py
import json
import datetime
import pdb

from specdb import defs
from specdb.build import utils as sdbbu

import igmspec
from igmspec.ingest import boss, hdlls, kodiaq, ggg, sdss, hst_z2, myers, twodf, xq100
from igmspec.ingest import hdla100
from igmspec.ingest import esidla
from igmspec.ingest import cos_halos
from igmspec.ingest import hst_qso
from igmspec.ingest import hst_cooksey as hst_c
from igmspec.ingest import cos_dwarfs
from igmspec.ingest import musodla
from igmspec.ingest import uves_dall

from astropy.table import Table, vstack, Column
from astropy import units as u

from linetools import utils as ltu

from specdb.specdb import IgmSpec

from igmspec.defs import get_survey_dict
survey_dict = get_survey_dict()


def ver01(test=False, mk_test_file=False, clobber=False, outfil=None, **kwargs):
    """ Build version 1.0

    Parameters
    ----------
    test : bool, optional
      Run test only
    mk_test_file : bool, optional
      Generate the test file for Travis tests?
      Writes catalog and HD-LLS dataset only

    Returns
    -------

    """
    version = 'v01'
    # HDF5 file
    if mk_test_file:
        outfil = igmspec.__path__[0]+'/tests/files/IGMspec_DB_{:s}_debug.hdf5'.format(version)
        print("Building debug file: {:s}".format(outfil))
        test = True
    else:
        outfil = igmspec.__path__[0]+'/../DB/IGMspec_DB_{:s}.hdf5'.format(version)
    # Chk clobber
    if os.path.isfile(outfil):
        if clobber:
            warnings.warn("Overwriting previous DB file {:s}".format(outfil))
        else:
            warnings.warn("Not overwiting previous DB file.  Set clobber=True if you wish")
            return
    # Begin
    hdf = h5py.File(outfil,'w')

    ''' Myers QSOs '''
    if True:
        igmsp = IgmSpec()
        igmsp.hdf.copy('quasars', hdf)
    else:
        myers.add_to_hdf(hdf)

    # Main DB Table
    idkey = 'IGM_ID'
    maindb, tkeys = sdbbu.start_maindb(idkey)

    # Group dict
    group_dict = {}


    ''' BOSS_DR12 '''
    # Read
    gname = 'BOSS_DR12'
    # Meta
    boss_meta = boss.grab_meta()
    # Survey flag
    flag_g = sdbbu.add_to_group_dict(gname, group_dict)
    # IDs -- BOSS DR12 has one pair with separation 1.2"
    maindb = sdbbu.add_ids(maindb, boss_meta, flag_g, tkeys, idkey, first=(flag_g==1))#, match_toler=1.1*u.arcsec)
    #
    if mk_test_file:
        maindb = maindb[:100]
    tmp=sdbbu.chk_for_duplicates(maindb) # Just do this for BOSS
    #if not test:
    if True:
        warnings.warn("INGEST BOSS SPECTRA!!")
    else:
        boss.hdf5_adddata(hdf, gname, boss_meta, **kwargs)

    ''' SDSS DR7'''
    gname = 'SDSS_DR7'
    print('===============\n Doing {:s} \n===============\n'.format(gname))
    sdss_meta = sdss.grab_meta(hdf)  # Need Myers
    # Survey flag
    flag_g = sdbbu.add_to_group_dict(gname, group_dict)
    # IDs
    maindb = sdbbu.add_ids(maindb, sdss_meta, flag_g, tkeys, idkey, first=(flag_g==1), close_pairs=True) # One at 1.7"
    # Spectra
    if False:
        warnings.warn("INGEST SDSS SPECTRA!!")
    else:
        sdss.hdf5_adddata(hdf, gname, sdss_meta, **kwargs)

    ''' KODIAQ DR1 '''
    sname = 'KODIAQ_DR1'
    print('==================\n Doing {:s} \n==================\n'.format(sname))
    kodiaq_meta = kodiaq.meta_for_build()
    # IDs
    kodiaq_cut, new, kodiaq_ids = sdbbu.set_new_ids(maindb, kodiaq_meta)
    nnew = np.sum(new)
    # Survey flag
    flag_s = survey_dict[sname]
    kodiaq_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
    midx = np.array(maindb['IGM_ID'][kodiaq_ids[~new]])
    maindb['flag_survey'][midx] += flag_s   # ASSUMES NOT SET ALREADY
    # Append
    assert sdbbu.chk_maindb_join(maindb, kodiaq_cut)
    maindb = vstack([maindb,kodiaq_cut], join_type='exact')
    # Update hf5 file
    if not test:
        kodiaq.hdf5_adddata(hdf, kodiaq_ids, sname)

    ''' HD-LLS '''
    sname = 'HD-LLS_DR1'
    print('===============\n Doing {:s} \n==============\n'.format(sname))
    # Read
    hdlls_meta = hdlls.meta_for_build()
    # IDs
    hdlls_cut, new, hdlls_ids = sdbbu.set_new_ids(maindb, hdlls_meta)
    nnew = np.sum(new)
    # Survey flag
    flag_s = survey_dict[sname]
    hdlls_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
    midx = np.array(maindb['IGM_ID'][hdlls_ids[~new]])
    maindb['flag_survey'][midx] += flag_s   # ASSUMES NOT SET ALREADY
    # Append
    assert sdbbu.chk_maindb_join(maindb, hdlls_cut)
    maindb = vstack([maindb,hdlls_cut], join_type='exact')
    # Update hf5 file
    if (not test) or mk_test_file:
        hdlls.hdf5_adddata(hdf, hdlls_ids, sname, mk_test_file=mk_test_file)

    ''' GGG '''
    sname = 'GGG'
    print('===============\n Doing {:s} \n==============\n'.format(sname))
    ggg_meta = ggg.meta_for_build()
    # IDs
    ggg_cut, new, ggg_ids = sdbbu.set_new_ids(maindb, ggg_meta)
    nnew = np.sum(new)
    # Survey flag
    flag_s = survey_dict[sname]
    ggg_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
    midx = np.array(maindb['IGM_ID'][ggg_ids[~new]])
    maindb['flag_survey'][midx] += flag_s   # ASSUMES NOT SET ALREADY
    # Append
    assert sdbbu.chk_maindb_join(maindb, ggg_cut)
    maindb = vstack([maindb,ggg_cut], join_type='exact')
    # Update hf5 file
    if not mk_test_file:
        ggg.hdf5_adddata(hdf, ggg_ids, sname)

    # Check for duplicates
    if not sdbbu.chk_for_duplicates(maindb):
        raise ValueError("Failed duplicates")

    # Check for junk
    zpri = defs.z_priority()

    # Finish
    hdf['catalog'] = maindb
    hdf['catalog'].attrs['NAME'] = 'igmspec'
    hdf['catalog'].attrs['EPOCH'] = 2000.
    hdf['catalog'].attrs['Z_PRIORITY'] = zpri
    hdf['catalog'].attrs['VERSION'] = version
    hdf['catalog'].attrs['CREATION_DATE'] = str(datetime.date.today().strftime('%Y-%b-%d'))
    hdfkeys = hdf.keys()
    for dkey in survey_dict.keys():
        if dkey not in hdfkeys:
            survey_dict.pop(dkey, None)
    hdf['catalog'].attrs['SURVEY_DICT'] = json.dumps(ltu.jsonify(survey_dict))
    hdf.close()
    print("Wrote {:s} DB file".format(outfil))
    print("Update DB info in specdb.defs.dbase_info !!")


def ver02(test=False, mk_test_file=False, skip_copy=False, clobber=False):
    """ Build version 2.X

    Reads previous datasets from v1.X

    Parameters
    ----------
    test : bool, optional
      Run test only
    mk_test_file : bool, optional
      Generate the test file for Travis tests?
      Writes catalog and HD-LLS dataset only
    skip_copy : bool, optional
      Skip copying the data from v01

    Returns
    -------
    """
    import os
    # Read v1.X
    #v01file = igmspec.__path__[0]+'/../DB/IGMspec_DB_v01.hdf5'
    v01file = os.getenv('IGMSPEC_DB')+'/IGMspec_DB_v01.hdf5'
    v01file_debug = igmspec.__path__[0]+'/tests/files/IGMspec_DB_v01_debug.hdf5'
    print("Loading v01")
    v01hdf = h5py.File(v01file,'r')
    maindb = Table(v01hdf['catalog'].value)

    # Start new file
    version = 'v02'
    if mk_test_file:
        outfil = igmspec.__path__[0]+'/tests/files/IGMspec_DB_{:s}_debug.hdf5'.format(version)
        print("Building debug file: {:s}".format(outfil))
        test = True
    else:
        outfil = igmspec.__path__[0]+'/../DB/IGMspec_DB_{:s}.hdf5'.format(version)
    # Chk clobber
    if os.path.isfile(outfil):
        if clobber:
            warnings.warn("Overwriting previous DB file {:s}".format(outfil))
        else:
            warnings.warn("Not overwiting previous DB file.  Set clobber=True to do so")
            return
    # Begin
    hdf = h5py.File(outfil,'w')

    # Copy over the old stuff
    if (not test) and (not skip_copy):
        for key in v01hdf.keys():
            if key == 'catalog':
                continue
            else:
                v01hdf.copy(key, hdf)
    if mk_test_file:
        v01hdf_debug = h5py.File(v01file_debug,'r')
        # Copy original
        for key in v01hdf_debug.keys():
            if key == 'catalog':
                dmaindb = v01hdf_debug[key].value
            else:
                v01hdf_debug.copy(key, hdf)
        # Add subset of quasars
        idx = np.array([False]*v01hdf['quasars'].size)
        idx[0:100] = True
        idx[161121] = True
        idx[161130] = True
        hdf['quasars'] = v01hdf['quasars'].value[idx]
        # Add some SDSS for script test
        bsdssi = np.where(maindb['flag_survey'] == 3)[0][0:10]
        sdss_meta = v01hdf['SDSS_DR7']['meta']
        sdssi = np.in1d(maindb['IGM_ID'][bsdssi], sdss_meta['IGM_ID'])
        hdf.create_group('SDSS_DR7')
        ibool = np.array([False]*len(sdss_meta))
        ibool[sdssi] = True
        # Generate
        hdf['SDSS_DR7']['meta'] = sdss_meta[ibool]
        hdf['SDSS_DR7']['spec'] = v01hdf['SDSS_DR7']['spec'][ibool]
        # Finish
        test = True
        maindb = dmaindb

    ''' UVpSM4 '''
    if not mk_test_file:
        sname = 'UVpSM4'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        hstc_meta = hst_c.meta_for_build()
        # IDs
        hstc_cut, new, hstc_ids = sdbbu.set_new_ids(maindb, hstc_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        hstc_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][hstc_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, hstc_cut)
        maindb = vstack([maindb, hstc_cut], join_type='exact')
        # Update hf5 file
        #if (not test):# or mk_test_file:
        hst_c.hdf5_adddata(hdf, hstc_ids, sname, mk_test_file=mk_test_file)

    ''' UVES_Dall '''
    if not mk_test_file:
        sname = 'UVES_Dall'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        uvesdall_meta = uves_dall.meta_for_build()
        # IDs
        uvesdall_cut, new, uvesdall_ids = sdbbu.set_new_ids(maindb, uvesdall_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        uvesdall_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][uvesdall_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, uvesdall_cut)
        maindb = vstack([maindb, uvesdall_cut], join_type='exact')
        # Update hf5 file
        uves_dall.hdf5_adddata(hdf, uvesdall_ids, sname)#, mk_test_file=mk_test_file)

    ''' HDLA100 '''
    if not mk_test_file:
        sname = 'HDLA100'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        hdla100_meta, _ = hdla100.meta_for_build()
        # IDs
        hdla100_cut, new, hdla100_ids = sdbbu.set_new_ids(maindb, hdla100_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        hdla100_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][hdla100_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, hdla100_cut)
        maindb = vstack([maindb, hdla100_cut], join_type='exact')
        # Update hf5 file
        hdla100.hdf5_adddata(hdf, hdla100_ids, sname)#, mk_test_file=mk_test_file)

    ''' MUSoDLA '''
    if not mk_test_file:
        sname = 'MUSoDLA'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        musodla_meta = musodla.meta_for_build()
        # IDs
        musodla_cut, new, musodla_ids = sdbbu.set_new_ids(maindb, musodla_meta)
        nnew = np.sum(new)
        assert nnew == 0   # These all should be in SDSS (although not necessarily the Schneider catalog)
        # Survey flag
        flag_s = survey_dict[sname]
        musodla_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][musodla_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, musodla_cut)
        maindb = vstack([maindb, musodla_cut], join_type='exact')
        # Update hf5 file
        musodla.hdf5_adddata(hdf, musodla_ids, sname)#, mk_test_file=mk_test_file)

    ''' HSTQSO '''
    if not mk_test_file:
        sname = 'HSTQSO'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        hstqso_meta = hst_qso.meta_for_build()
        # IDs
        hstqso_cut, new, hstqso_ids = sdbbu.set_new_ids(maindb, hstqso_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        hstqso_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][hstqso_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, hstqso_cut)
        maindb = vstack([maindb, hstqso_cut], join_type='exact')
        # Update hf5 file
        hst_qso.hdf5_adddata(hdf, hstqso_ids, sname)#, mk_test_file=mk_test_file)

    ''' COS-Dwarfs '''
    if not mk_test_file:
        sname = 'COS-Dwarfs'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        cdwarfs_meta = cos_dwarfs.meta_for_build()
        # IDs
        cdwarfs_cut, new, cdwarfs_ids = sdbbu.set_new_ids(maindb, cdwarfs_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        cdwarfs_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][cdwarfs_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, cdwarfs_cut)
        maindb = vstack([maindb, cdwarfs_cut], join_type='exact')
        # Update hf5 file
        cos_dwarfs.hdf5_adddata(hdf, cdwarfs_ids, sname)#, mk_test_file=mk_test_file)

    ''' 2QZ '''
    if not mk_test_file:
        sname = '2QZ'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        tdf_meta = twodf.meta_for_build()
        # IDs
        tdf_cut, new, tdf_ids = sdbbu.set_new_ids(maindb, tdf_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        tdf_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][tdf_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, tdf_cut)
        maindb = vstack([maindb,tdf_cut], join_type='exact')
        # Update hf5 file
        twodf.hdf5_adddata(hdf, tdf_ids, sname)

    ''' COS-Halos '''
    if not mk_test_file:
        sname = 'COS-Halos'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        chalos_meta = cos_halos.meta_for_build()
        # IDs
        chalos_cut, new, chalos_ids = sdbbu.set_new_ids(maindb, chalos_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        chalos_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][chalos_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, chalos_cut)
        maindb = vstack([maindb, chalos_cut], join_type='exact')
        # Update hf5 file
        cos_halos.hdf5_adddata(hdf, chalos_ids, sname)#, mk_test_file=mk_test_file)


    ''' ESI-DLA '''
    if not mk_test_file:
        sname = 'ESI_DLA'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        esidla_meta = esidla.meta_for_build()
        # IDs
        esidla_cut, new, esidla_ids = sdbbu.set_new_ids(maindb, esidla_meta)
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        esidla_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][esidla_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, esidla_cut)
        maindb = vstack([maindb, esidla_cut], join_type='exact')
        # Update hf5 file
        esidla.hdf5_adddata(hdf, esidla_ids, sname)#, mk_test_file=mk_test_file)

    ''' XQ-100 '''
    if not mk_test_file:
        sname = 'XQ-100'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        xq100_meta = xq100.meta_for_build()
        # IDs
        xq100_cut, new, xq100_ids = sdbbu.set_new_ids(maindb, xq100_meta, mtch_toler=10*u.arcsec)  # BAD COORD!!
        nnew = np.sum(new)
        # Survey flag
        flag_s = survey_dict[sname]
        xq100_cut.add_column(Column([flag_s]*nnew, name='flag_survey'))
        midx = np.array(maindb['IGM_ID'][xq100_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Append
        assert sdbbu.chk_maindb_join(maindb, xq100_cut)
        maindb = vstack([maindb, xq100_cut], join_type='exact')
        # Update hf5 file
        xq100.hdf5_adddata(hdf, xq100_ids, sname)#, mk_test_file=mk_test_file)


    ''' HST_z2 '''
    if not mk_test_file:
        sname = 'HST_z2'
        print('===============\n Doing {:s} \n==============\n'.format(sname))
        # Read
        hstz2_meta = hst_z2.meta_for_build()
        # IDs
        hstz2_cut, new, hstz2_ids = sdbbu.set_new_ids(maindb, hstz2_meta)
        nnew = np.sum(new)
        if nnew > 0:
            raise ValueError("All of these should be in SDSS")
        # Survey flag
        flag_s = survey_dict[sname]
        midx = np.array(maindb['IGM_ID'][hstz2_ids[~new]])
        maindb['flag_survey'][midx] += flag_s
        # Update hf5 file
        hst_z2.hdf5_adddata(hdf, hstz2_ids, sname, mk_test_file=mk_test_file)

    # Finish
    hdf['catalog'] = maindb
    hdf['catalog'].attrs['NAME'] = 'igmspec'
    hdf['catalog'].attrs['EPOCH'] = 2000.
    zpri = v01hdf['catalog'].attrs['Z_PRIORITY']
    hdf['catalog'].attrs['Z_PRIORITY'] = zpri
    hdf['catalog'].attrs['VERSION'] = version
    hdf['catalog'].attrs['CREATION_DATE'] = str(datetime.date.today().strftime('%Y-%b-%d'))
    hdfkeys = hdf.keys()
    for dkey in survey_dict.keys():
        if dkey not in hdfkeys:
            survey_dict.pop(dkey, None)
    hdf['catalog'].attrs['SURVEY_DICT'] = json.dumps(ltu.jsonify(survey_dict))
    hdf.close()
    print("Wrote {:s} DB file".format(outfil))
    print("Update DB info in specdb.defs.dbase_info !!")

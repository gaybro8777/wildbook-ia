"""
displays results from experiment_harness
"""
from __future__ import absolute_import, division, print_function
import itertools
import numpy as np
import six
import utool as ut
from ibeis import ibsfuncs
from ibeis.dev import experiment_helpers as eh
from ibeis.model.hots import match_chips4 as mc4
from itertools import chain
from os.path import join, dirname, split, basename, splitext
from plottool import draw_func2 as df2
from plottool import plot_helpers as ph
from six.moves import map, range, input  # NOQA
import vtool as vt
from ibeis import params
print, print_, printDBG, rrr, profile = ut.inject(__name__, '[expt_report]')


SKIP_TO = ut.get_argval(('--skip-to', '--skipto'), type_=int, default=None)
#SAVE_FIGURES = ut.get_argflag(('--save-figures', '--sf'))
SAVE_FIGURES = not ut.get_argflag(('--nosave-figures', '--nosf'))

VIEW_FIG_DIR         = ut.get_argflag(('--view-fig-dir', '--vf'))
QUERY_ANALYSIS_DNAME = ut.get_argval('--fig-dname', str, 'query_analysis')
DUMP_EXTRA           = ut.get_argflag('--dump-extra')
QUALITY              = ut.get_argflag('--quality')
SHOW                 = ut.get_argflag('--show')

# only triggered if dump_extra is on
DUMP_PROBCHIP = False
DUMP_REGCHIP = False


def get_diffranks(rank_mat, qaids):
    """ Find rows which scored differently over the various configs """
    isdiff_flags = [not np.all(row == row[0]) for row in rank_mat]
    diff_aids = ut.list_compress(qaids, isdiff_flags)
    diff_rank = rank_mat.compress(isdiff_flags, axis=0)
    diff_qxs  = np.where(isdiff_flags)[0]
    return diff_aids, diff_rank, diff_qxs


def get_interesting_ranks(rank_mat, qaids):
    # find the rows that vary greatest with the parameter settings
    diff_aids, diff_rank, diff_qxs = get_diffranks(rank_mat, qaids)
    if False:
        rankcategory = np.log(diff_rank + 1)
    else:
        rankcategory = diff_rank.copy()
        rankcategory[diff_rank == 0]  = 0
        rankcategory[diff_rank > 0]   = 1
        rankcategory[diff_rank > 2]   = 2
        rankcategory[diff_rank > 5]   = 3
        rankcategory[diff_rank > 50]  = 4
        rankcategory[diff_rank > 100] = 5
    row_rankcategory_std = np.std(rankcategory, axis=1)
    row_rankcategory_mean = np.mean(rankcategory, axis=1)
    row_sortx = vt.argsort_multiarray([row_rankcategory_std, row_rankcategory_mean], reverse=True)

    interesting_qx_list = diff_qxs.take(row_sortx).tolist()
    #print("INTERSETING MEASURE")
    #print(interesting_qx_list)
    #print(row_rankcategory_std)
    #print(ut.list_take(qaids, row_sortx))
    #print(diff_rank.take(row_sortx, axis=0))
    return interesting_qx_list


def get_diffmat_str(rank_mat, qaids, nConfig):
    diff_aids, diff_rank, diff_qxs = get_diffranks(rank_mat, qaids)
    # Find columns that ore strictly better than other columns
    #def find_strictly_better_columns(diff_rank):
    #    colmat = diff_rank.T
    #    pairwise_betterness_ranks = np.array([np.sum(col <= colmat, axis=1) / len(col) for col in colmat], dtype=np.float).T
    diff_mat = np.vstack((diff_aids, diff_rank.T)).T
    col_lbls = list(chain(['qaid'], map(lambda x: 'cfg%d_rank' % x, range(nConfig))))
    col_type  = list(chain([int], [int] * nConfig))
    header = 'diffmat'
    diff_matstr = ut.numpy_to_csv(diff_mat, col_lbls, header, col_type)
    return diff_matstr


@profile
def draw_results(ibs, test_result):
    """
    Draws results from an experiment harness run.
    Rows store different qaids (query annotation ids)
    Cols store different configurations (algorithm parameters)

    CommandLine:
        python dev.py -t custom:rrvsone_on=True,constrained_coeff=0 custom --qaid 12 --db PZ_MTEST --show --va
        python dev.py -t custom:rrvsone_on=True,constrained_coeff=.3 custom --qaid 12 --db PZ_MTEST --show --va --noqcache
        python dev.py -t custom:rrvsone_on=True custom --qaid 4 --db PZ_MTEST --show --va --noqcache

        python dev.py -t custom:rrvsone_on=True,grid_scale_factor=1 custom --qaid 12 --db PZ_MTEST --show --va --noqcache
        python dev.py -t custom:rrvsone_on=True,grid_scale_factor=1,grid_steps=1 custom --qaid 12 --db PZ_MTEST --show --va --noqcache

    CommandLine:
        python dev.py -t best --db seals2 --allgt --vz --fig-dname query_analysis_easy --show
        python dev.py -t best --db seals2 --allgt --vh --fig-dname query_analysis_hard --show
        python dev.py -t pyrscale --db PZ_MTEST --allgt --vn --fig-dname query_analysis_interesting --show

        python -m ibeis.dev.experiment_printres --test-draw_results --show --vn
        python -m ibeis.dev.experiment_printres --test-draw_results --show --vn --db PZ_MTEST

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.dev.experiment_printres import *  # NOQA
        >>> from ibeis.dev import experiment_harness
        >>> import ibeis
        >>> # build test data
        >>> species = ibeis.const.Species.ZEB_PLAIN
        >>> #ibs = ibeis.opendb(defaultdb='PZ_MTEST')
        >>> ibs = ibeis.opendb(defaultdb='testdb3')
        >>> test_cfg_name_list = ['pyrscale']
        >>> qaids = ibs.get_valid_aids(species=species, hasgt=True)
        >>> daids = ibs.get_valid_aids(species=species)
        >>> test_result = experiment_harness.run_test_configurations(ibs, qaids, daids, test_cfg_name_list)
        >>> # execute function
        >>> result = draw_results(ibs, test_result)
        >>> # verify results
        >>> print(result)
    """
    print(' --- DRAW RESULTS ---')

    # It is very inefficient to turn off caching when view_all is true
    if not mc4.USE_CACHE:
        print('WARNING: view_all specified with USE_CACHE == False')
        print('WARNING: we will try to turn cache on when reloading results')
        #mc4.USE_CACHE = True

    qaids = test_result.qaids
    daids = test_result.daids
    new_hard_qx_list = test_result.get_new_hard_qx_list()
    rank_mat = test_result.get_rank_mat()
    interesting_qx_list = get_interesting_ranks(rank_mat, qaids)

    (cfg_list, cfgx2_lbl, cfgx2_qreq_) = ut.dict_take(
        test_result.__dict__, ['cfg_list', 'cfgx2_lbl', 'cfgx2_qreq_'])

    #_viewkw = dict(view_interesting=True)
    _viewkw = {}
    sel_rows, sel_cols = get_sel_rows_and_cols(qaids, cfg_list, new_hard_qx_list, interesting_qx_list, **_viewkw)

    skip_list = []
    cp_src_list = []
    cp_dst_list = []

    figdir = join(ibs.get_fig_dir(), QUERY_ANALYSIS_DNAME)
    ut.ensuredir(ibs.get_fig_dir())
    ut.ensuredir(figdir)

    if VIEW_FIG_DIR:
        ut.view_directory(figdir, verbose=True)

    def append_copy_task(fpath_orig):
        """ helper which copies a summary figure to root dir """
        fname_orig, ext = splitext(basename(fpath_orig))
        outdir = dirname(fpath_orig)
        fdir_clean, cfgdir = split(outdir)
        #aug = cfgdir[0:min(len(cfgdir), 10)]
        aug = cfgdir
        fname_fmt = '{aug}_{fname_orig}{ext}'
        fmt_dict = {'aug': aug, 'fname_orig': fname_orig, 'ext': ext}
        fname_clean = ut.long_fname_format(fname_fmt, fmt_dict, ['fname_orig'], max_len=128)
        fdst_clean = join(fdir_clean, fname_clean)
        cp_src_list.append(fpath_orig)
        cp_dst_list.append(fdst_clean)

    def flush_copy_tasks():
        # Execute all copy tasks and empty the lists
        print('[DRAW_RESULT] copying %r summaries' % (len(cp_src_list)))
        for src, dst in zip(cp_src_list, cp_dst_list):
            ut.copy(src, dst, verbose=False)
        del cp_dst_list[:]
        del cp_src_list[:]

    def load_qres(ibs, qaid, daids, qreq_):
        # Load / Execute the query w/ correct config
        qreq_.set_external_qaids([qaid])
        qres = ibs._query_chips4(
            [qaid], daids, use_cache=True, use_bigcache=False,
            qreq_=qreq_)[qaid]
        return qres

    def _show_chip(aid, prefix, rank=None, in_image=False, seen=set([]), config2_=None, **dumpkw):
        print('[PRINT_RESULTS] show_chip(aid=%r) prefix=%r' % (aid, prefix))
        from ibeis import viz
        # only dump a chip that hasn't been dumped yet
        if aid in seen:
            print('[PRINT_RESULTS] SEEN SKIPPING')
            return
        fulldir = join(figdir, dumpkw['subdir'])
        if DUMP_PROBCHIP:
            # just copy it
            probchip_fpath = ibs.get_annot_probchip_fpath([aid], config2_=config2_)[0]
            ut.copy(probchip_fpath, fulldir, overwrite=False)
        if DUMP_REGCHIP:
            chip_fpath = ibs.get_annot_chip_fpath([aid], config2_=config2_)[0]
            ut.copy(chip_fpath, fulldir, overwrite=False)

        viz.show_chip(ibs, aid, in_image=in_image, config2_=config2_)
        if rank is not None:
            prefix += 'rank%d_' % rank
        df2.set_figtitle(prefix + ibs.annotstr(aid))
        seen.add(aid)
        if ut.VERBOSE:
            print('[expt] dumping fig to %s' % figdir)

        fpath_clean = ph.dump_figure(figdir, **dumpkw)
        return fpath_clean

    if True:
        for r in ut.InteractiveIter(sel_rows, enabled=SHOW):
            qreq_list = ut.list_take(cfgx2_qreq_, sel_cols)
            qres_list = [load_qres(ibs, qaids[r], daids, qreq_) for qreq_ in qreq_list]

            print(rank_mat[r])

            for c, qres, qreq_ in zip(sel_cols, qres_list, qreq_list):
                fnum = c if SHOW else 1
                # Get row and column index
                query_lbl = cfgx2_lbl[c]
                qres_cfg = qres.get_fname(ext='')
                subdir = qres_cfg
                # Draw Result
                dumpkw = {
                    'subdir'    : subdir,
                    'quality'   : QUALITY,
                    'overwrite' : True,
                    'verbose'   : 0,
                }
                show_kwargs = {
                    'N': 3,
                    'ori': True,
                    'ell_alpha': .9,
                }

                # Show Figure
                # try to shorten query labels a bit
                query_lbl = query_lbl.replace(' ', '').replace('\'', '')
                #qres.show(ibs, 'analysis', figtitle=query_lbl, fnum=fnum, **show_kwargs)
                if SHOW:
                    qres.ishow_analysis(ibs, figtitle=query_lbl, fnum=fnum, annot_mode=1, qreq_=qreq_, **show_kwargs)
                    #qres.show_analysis(ibs, figtitle=query_lbl, fnum=fnum, annot_mode=1, qreq_=qreq_, **show_kwargs)
                else:
                    qres.show_analysis(ibs, figtitle=query_lbl, fnum=fnum, annot_mode=1, qreq_=qreq_, **show_kwargs)

                # Adjust subplots
                #df2.adjust_subplots_safe()
                fpath_orig = ph.dump_figure(figdir, reset=not SHOW, **dumpkw)
                #append_copy_task(fpath_orig)

            # if some condition of of batch sizes
            # flush_copy_tasks()
        #flush_copy_tasks()
    else:
        chunksize = 4
        # <FOR RCITER_CHUNK>
        #with ut.EmbedOnException():
        def is_skipped(count):
            return (count in skip_list) or (SKIP_TO and count < SKIP_TO)

        total = len(sel_cols) * len(sel_rows)
        rciter = list(itertools.product(sel_rows, sel_cols))
        for rciter_chunk in ut.ichunks(enumerate(rciter), chunksize):
            # First load a chunk of query results
            # <FOR RCITER>
            qreq_list = [cfgx2_qreq_[c] for count, (r, c) in rciter_chunk if not is_skipped(count)]
            qres_list = [load_qres(ibs, qaids[r], daids, cfgx2_qreq_[c])
                         for count, (r, c) in rciter_chunk if not is_skipped(count)]

            # Iterate over chunks a second time, but
            # with loaded query results
            for (count, rctup), qres, qreq_ in zip(rciter_chunk, qres_list, qreq_list):
                if (count in skip_list) or (SKIP_TO and count < SKIP_TO):
                    continue
                (r, c) = rctup
                fnum = c if SHOW else 1
                # Get row and column index
                query_lbl = cfgx2_lbl[c]
                print(ut.unindent('''
                __________________________________
                --- VIEW %d / %d --- (r=%r, c=%r)
                ----------------------------------
                ''')  % (count + 1, total, r, c))
                qres_cfg = qres.get_fname(ext='')
                subdir = qres_cfg
                # Draw Result
                dumpkw = {
                    'subdir'    : subdir,
                    'quality'   : QUALITY,
                    'overwrite' : True,
                    'verbose'   : 0,
                }
                show_kwargs = {
                    'N': 3,
                    'ori': True,
                    'ell_alpha': .9,
                }

                #if not SAVE_FIGURES:
                #    continue

                #if USE_FIGCACHE and ut.checkpath(join(figdir, subdir)):
                #    pass

                print('[harn] drawing analysis plot')

                # Show Figure
                # try to shorten query labels a bit
                query_lbl = query_lbl.replace(' ', '').replace('\'', '')
                #qres.show(ibs, 'analysis', figtitle=query_lbl, fnum=fnum, **show_kwargs)
                if SHOW:
                    qres.ishow_analysis(ibs, figtitle=query_lbl, fnum=fnum, annot_mode=1, qreq_=qreq_, **show_kwargs)
                    #qres.show_analysis(ibs, figtitle=query_lbl, fnum=fnum, annot_mode=1, qreq_=qreq_, **show_kwargs)
                else:
                    qres.show_analysis(ibs, figtitle=query_lbl, fnum=fnum, annot_mode=1, qreq_=qreq_, **show_kwargs)

                # Adjust subplots
                #df2.adjust_subplots_safe()

                if SHOW:
                    print('[DRAW_RESULT] df2.present()')
                    # Draw only once we finish drawing all configs (columns) for
                    # this row (query)
                    if c == len(sel_cols) - 1:
                        #execstr = df2.present()  # NOQA
                        ans = input('press to continue...')
                        if ans == 'cmd':
                            ut.embed()
                        #six.exec_(execstr, globals(), locals())
                        #exec(df2.present(), globals(), locals())
                    #print(execstr)
                # Saving will close the figure
                fpath_orig = ph.dump_figure(figdir, reset=not SHOW, **dumpkw)
                append_copy_task(fpath_orig)

                print('[harn] drawing extra plots')

                DUMP_QANNOT         = DUMP_EXTRA
                if DUMP_QANNOT:
                    _show_chip(qres.qaid, 'QUERY_', config2_=qreq_.qparams, **dumpkw)
                    _show_chip(qres.qaid, 'QUERY_CXT_', in_image=True, config2_=qreq_.get_external_query_config2(), **dumpkw)

                DUMP_QANNOT_DUMP_GT = DUMP_EXTRA
                if DUMP_QANNOT_DUMP_GT:
                    gtaids = ibs.get_annot_groundtruth(qres.qaid)
                    for aid in gtaids:
                        rank = qres.get_aid_ranks(aid)
                        _show_chip(aid, 'GT_CXT_', rank=rank, in_image=True, config2_=qreq_.get_external_data_config2(), **dumpkw)

                DUMP_TOP_CONTEXT    = DUMP_EXTRA
                if DUMP_TOP_CONTEXT:
                    topids = qres.get_top_aids(num=3)
                    for aid in topids:
                        rank = qres.get_aid_ranks(aid)
                        _show_chip(aid, 'TOP_CXT_', rank=rank, in_image=True, config2_=qreq_.get_external_data_config2(), **dumpkw)
            flush_copy_tasks()
        # </FOR RCITER>

        # Copy summary images to query_analysis folder
        flush_copy_tasks()

    if ut.NOT_QUIET:
        print('[DRAW_RESULT] EXIT EXPERIMENT HARNESS')


@profile
def print_results(ibs, test_result):
    """
    Prints results from an experiment harness run.
    Rows store different qaids (query annotation ids)
    Cols store different configurations (algorithm parameters)

    CommandLine:
        python dev.py -t best --db seals2 --allgt --vz

        python dev.py --db PZ_MTEST --allgt -t custom --print-confusion-stats

        python dev.py --db PZ_MTEST --allgt --noqcache --index 0:10:2 -t custom:rrvsone_on=True --print-scorediff-mat-stats
        python dev.py --db PZ_MTEST --allgt --noqcache --index 0:10:2 -t custom:rrvsone_on=True --print-scorediff-mat-stats
        python dev.py --db PZ_MTEST --allgt --noqcache --index 0:10:2 -t custom:rrvsone_on=True --print-confusion-stats --print-scorediff-mat-stats

        python dev.py --db PZ_MTEST --allgt --noqcache --index 0:10:2 -t custom:rrvsone_on=True --print-confusion-stats
        python dev.py --db PZ_MTEST --allgt --noqcache --qaid4 -t custom:rrvsone_on=True --print-confusion-stats

    CommandLine:
        python -m ibeis.dev.experiment_printres --test-print_results
        utprof.py -m ibeis.dev.experiment_printres --test-print_results

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.dev.experiment_printres import *  # NOQA
        >>> from ibeis.dev import experiment_harness
        >>> import ibeis
        >>> # build test data
        >>> species = ibeis.const.Species.ZEB_PLAIN
        >>> #ibs = ibeis.opendb(defaultdb='PZ_MTEST')
        >>> ibs = ibeis.opendb(defaultdb='testdb3')
        >>> test_cfg_name_list = ['pyrscale']
        >>> qaids = ibs.get_valid_aids(species=species, hasgt=True)
        >>> daids = ibs.get_valid_aids(species=species)
        >>> test_result = experiment_harness.run_test_configurations(ibs, qaids, daids, test_cfg_name_list)
        >>> # execute function
        >>> result = print_results(ibs, test_result)
        >>> # verify results
        >>> print(result)
    """
    qaids = test_result.qaids
    (cfg_list, cfgx2_cfgresinfo, testnameid, cfgx2_lbl, cfgx2_qreq_) = ut.dict_take(
        test_result.__dict__, ['cfg_list', 'cfgx2_cfgresinfo', 'testnameid', 'cfgx2_lbl', 'cfgx2_qreq_'])

    # cfgx2_cfgresinfo is a list of dicts of lists
    # Parse result info out of the lists
    cfgx2_nextbestranks  = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_next_bestranks')
    cfgx2_gt_rawscores   = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_gt_raw_score')
    cfgx2_gf_rawscores   = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_gf_raw_score')
    cfgx2_aveprecs       = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_avepercision')

    cfgx2_scorediffs     = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_scorediff')
    cfgx2_scorefactor    = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_scorefactor')
    cfgx2_scorelogfactor = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_scorelogfactor')
    cfgx2_scoreexpdiff   = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_scoreexpdiff')
    cfgx2_gt_raw_score   = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_gt_raw_score')

    column_lbls = [ut.remove_chars(ut.remove_vowels(lbl), [' ', ','])
                   for lbl in cfgx2_lbl]

    scorediffs_mat     = np.array(ut.replace_nones(cfgx2_scorediffs, np.nan))
    scorefactor_mat    = np.array(ut.replace_nones(cfgx2_scorefactor, np.nan))
    scorelogfactor_mat = np.array(ut.replace_nones(cfgx2_scorelogfactor, np.nan))
    scoreexpdiff_mat   = np.array(ut.replace_nones(cfgx2_scoreexpdiff, np.nan))

    print(' --- PRINT RESULTS ---')
    # Num of ranks less than to score
    X_LIST = [1]
    #X_LIST = [1, 5]

    nConfig = len(cfg_list)
    nQuery = len(qaids)
    #--------------------

    gt_raw_score_mat = np.vstack(cfgx2_gt_raw_score).T
    rank_mat = test_result.get_rank_mat()

    # A positive scorediff indicates the groundtruth was better than the
    # groundfalse scores
    istrue_list  = [scorediff > 0 for scorediff in scorediffs_mat]
    isfalse_list = [~istrue for istrue in istrue_list]

    # Label the rank matrix:
    _colxs = np.arange(nConfig)
    lbld_mat = ut.debug_vstack([_colxs, rank_mat])

    _rowxs = np.arange(nQuery + 1).reshape(nQuery + 1, 1) - 1
    lbld_mat = np.hstack([_rowxs, lbld_mat])
    #------------
    # Build row lbls
    qx2_lbl = np.array([
        'qx=%d) q%s ' % (qx, ibsfuncs.aidstr(qaids[qx], ibs=ibs, notes=True))
        for qx in range(nQuery)])

    #------------
    # Build Colscore and hard cases
    qx2_min_rank = []
    qx2_argmin_rank = []
    new_hard_qaids = []
    new_hardtup_list = []

    for qx in range(nQuery):
        ranks = rank_mat[qx]
        valid_ranks = ranks[ranks >= 0]
        min_rank = ranks.min() if len(valid_ranks) > 0 else -3
        bestCFG_X = np.where(ranks == min_rank)[0]
        qx2_min_rank.append(min_rank)
        # Find the best rank over all configurations
        qx2_argmin_rank.append(bestCFG_X)

    new_hard_qx_list = test_result.get_new_hard_qx_list()

    for qx in new_hard_qx_list:
        # New list is in aid format instead of cx format
        # because you should be copying and pasting it
        notes = ' ranks = ' + str(rank_mat[qx])
        qaid = qaids[qx]
        name = ibs.get_annot_names(qaid)
        new_hardtup_list += [(qaid, name + " - " + notes)]
        new_hard_qaids += [qaid]

    #------------
    # Build Colscore
    # Build a dictionary mapping X (as in #ranks < X) to a list of cfg scores
    nLessX_dict = {int(X): np.zeros(nConfig) for X in X_LIST}
    for X in X_LIST:
        lessX_ = np.logical_and(np.less(rank_mat, X), np.greater_equal(rank_mat, 0))
        nLessX_dict[int(X)] = lessX_.sum(axis=0)

    @ut.argv_flag_dec
    def print_rowlbl():
        print('=====================')
        print('[harn] Row/Query Labels: %s' % testnameid)
        print('=====================')
        print('[harn] queries:\n%s' % '\n'.join(qx2_lbl))
        print('--- /Row/Query Labels ---')
    print_rowlbl()
    #------------

    @ut.argv_flag_dec
    def print_collbl():
        print('=====================')
        print('[harn] Col/Config Labels: %s' % testnameid)
        print('=====================')
        enum_cfgx2_lbl = ['%2d) %s' % (count, cfglbl)
                            for count, cfglbl in enumerate(cfgx2_lbl)]
        print('[harn] cfglbl:\n%s' % '\n'.join(enum_cfgx2_lbl))
        print('--- /Col/Config Labels ---')
    print_collbl()

    #------------

    @ut.argv_flag_dec_true
    def print_cfgstr():
        print('=====================')
        print('[harn] Config Strings: %s' % testnameid)
        print('=====================')
        cfgstr_list = [query_cfg.get_cfgstr() for query_cfg in cfg_list]
        enum_cfgstr_list = ['%2d) %s' % (count, cfgstr)
                            for count, cfgstr in enumerate(cfgstr_list)]
        print('\n[harn] cfgstr:\n%s' % '\n'.join(enum_cfgstr_list))
        print('--- /Config Strings ---')
    print_cfgstr()

    #------------

    @ut.argv_flag_dec
    def print_rowscore():
        print('=======================')
        print('[harn] Scores per Query: %s' % testnameid)
        print('=======================')
        for qx in range(nQuery):
            bestCFG_X = qx2_argmin_rank[qx]
            min_rank = qx2_min_rank[qx]
            minimizing_cfg_str = ut.indentjoin(cfgx2_lbl[bestCFG_X], '\n  * ')
            #minimizing_cfg_str = str(bestCFG_X)

            print('-------')
            print(qx2_lbl[qx])
            print(' best_rank = %d ' % min_rank)
            if len(cfgx2_lbl) != 1:
                print(' minimizing_cfg_x\'s = %s ' % minimizing_cfg_str)
    print_rowscore()

    #------------

    @ut.argv_flag_dec
    def print_row_ave_precision():
        print('=======================')
        print('[harn] Scores per Query: %s' % testnameid)
        print('=======================')
        for qx in range(nQuery):
            aveprecs = ', '.join(['%.2f' % (aveprecs[qx],) for aveprecs in cfgx2_aveprecs])
            print('-------')
            print(qx2_lbl[qx])
            print(' aveprecs = %s ' % aveprecs)
    print_row_ave_precision()

    #------------

    @ut.argv_flag_dec
    def print_hardcase():
        print('===')
        print('--- hard new_hardtup_list (w.r.t these configs): %s' % testnameid)
        print('\n'.join(map(repr, new_hardtup_list)))
        print('There are %d hard cases ' % len(new_hardtup_list))
        aid_list = [aid_notes[0] for aid_notes in new_hardtup_list]
        name_list = ibs.get_annot_names(aid_list)
        name_set = set(name_list)
        print(sorted(aid_list))
        print('Names: %r' % (name_set,))
        print('--- /Print Hardcase ---')
    print_hardcase()
    #default=not ut.get_argflag('--allhard'))

    #------------

    @ut.argv_flag_dec_true
    def echo_hardcase():
        print('====')
        print('--- hardcase commandline: %s' % testnameid)
        # Show index for current query where hardids reside
        #print('--index ' + (' '.join(map(str, new_hard_qx_list))))
        #print('--take new_hard_qx_list')
        #hardaids_str = ' '.join(map(str, ['    ', '--qaid'] + new_hard_qaids))
        hardaids_str = ' '.join(map(str, ['    ', '--set-aids-as-hard'] + new_hard_qaids))
        print(hardaids_str)
        print('--- /Echo Hardcase ---')
    echo_hardcase(default=not ut.get_argflag('--allhard'))

    #------------

    @ut.argv_flag_dec
    def print_colmap():
        print('==================')
        print('[harn] mAP per Config: %s (sorted by mAP)' % testnameid)
        print('==================')
        cfgx2_mAP = np.array([aveprec_list.mean() for aveprec_list in cfgx2_aveprecs])
        sortx = cfgx2_mAP.argsort()
        for cfgx in sortx:
            print('[mAP] cfgx=%r) mAP=%.3f -- %s' % (cfgx, cfgx2_mAP[cfgx], cfgx2_lbl[cfgx]))
        #print('--- /Scores per Config ---')
    print_colmap()
    #------------

    @ut.argv_flag_dec_true
    def print_colscore():
        print('==================')
        print('[harn] Scores per Config: %s' % testnameid)
        print('==================')
        #for cfgx in range(nConfig):
        #    print('[score] %s' % (cfgx2_lbl[cfgx]))
        #    for X in X_LIST:
        #        nLessX_ = nLessX_dict[int(X)][cfgx]
        #        print('        ' + eh.rankscore_str(X, nLessX_, nQuery))
        print('\n[harn] ... sorted scores')
        for X in X_LIST:
            print('\n[harn] Sorted #ranks < %r scores' % (X))
            sortx = np.array(nLessX_dict[int(X)]).argsort()
            for cfgx in sortx:
                nLessX_ = nLessX_dict[int(X)][cfgx]
                rankstr = eh.rankscore_str(X, nLessX_, nQuery, withlbl=False)
                print('[score] %s --- %s' % (rankstr, cfgx2_lbl[cfgx]))
        print('--- /Scores per Config ---')
    print_colscore()

    #------------

    @ut.argv_flag_dec
    def print_latexsum():
        print('==========================')
        print('[harn] LaTeX: %s' % testnameid)
        print('==========================')
        # Create configuration latex table
        criteria_lbls = ['#ranks < %d' % X for X in X_LIST]
        dbname = ibs.get_dbname()
        cfg_score_title = dbname + ' rank scores'
        cfgscores = np.array([nLessX_dict[int(X)] for X in X_LIST]).T

        replace_rowlbl = [(' *cfgx *', ' ')]
        tabular_kwargs = dict(title=cfg_score_title, out_of=nQuery,
                              bold_best=True, replace_rowlbl=replace_rowlbl,
                              flip=True)
        tabular_str = ut.util_latex.make_score_tabular(cfgx2_lbl,
                                                          criteria_lbls,
                                                          cfgscores,
                                                          **tabular_kwargs)
        #latex_formater.render(tabular_str)
        print(tabular_str)
        print('--- /LaTeX ---')
    #print_latexsum()

    #------------
    best_rankscore_summary = []
    to_intersect_list = []
    # print each configs scores less than X=thresh
    for X, cfgx2_nLessX in six.iteritems(nLessX_dict):
        max_LessX = cfgx2_nLessX.max()
        bestCFG_X = np.where(cfgx2_nLessX == max_LessX)[0]
        best_rankscore = '[cfg*] %d cfg(s) scored ' % len(bestCFG_X)
        best_rankscore += eh.rankscore_str(X, max_LessX, nQuery)
        best_rankscore_summary += [best_rankscore]
        to_intersect_list += [cfgx2_lbl[bestCFG_X]]

    intersected = to_intersect_list[0] if len(to_intersect_list) > 0 else []
    for ix in range(1, len(to_intersect_list)):
        intersected = np.intersect1d(intersected, to_intersect_list[ix])

    @ut.argv_flag_dec
    def print_bestcfg():
        print('==========================')
        print('[harn] Best Configurations: %s' % testnameid)
        print('==========================')
        # print each configs scores less than X=thresh
        for X, cfgx2_nLessX in six.iteritems(nLessX_dict):
            max_LessX = cfgx2_nLessX.max()
            bestCFG_X = np.where(cfgx2_nLessX == max_LessX)[0]
            best_rankscore = '[cfg*] %d cfg(s) scored ' % len(bestCFG_X)
            best_rankscore += eh.rankscore_str(X, max_LessX, nQuery)
            cfglbl_list = cfgx2_lbl[bestCFG_X]

            best_rankcfg = eh.format_cfgstr_list(cfglbl_list)
            #indent('\n'.join(cfgstr_list), '    ')
            print(best_rankscore)
            print(best_rankcfg)
        print('[cfg*]  %d cfg(s) are the best of %d total cfgs' % (len(intersected), nConfig))
        print(eh.format_cfgstr_list(intersected))

        print('--- /Best Configurations ---')
    print_bestcfg()

    #------------

    @ut.argv_flag_dec
    def print_gtscore():
        # Prints best ranks
        print('-------------')
        print('gtscore_mat: %s' % testnameid)
        print(' nRows=%r, nCols=%r' % lbld_mat.shape)
        header = (' labled rank matrix: rows=queries, cols=cfgs:')
        #print('\n'.join(qx2_lbl))
        print('\n'.join(cfgx2_lbl))
        #column_list = [row.tolist() for row in lbld_mat[1:].T[1:]]
        column_list = gt_raw_score_mat.T
        print(ut.make_csv_table(column_list, row_lbls=qaids,
                                column_lbls=column_lbls, header=header,
                                transpose=False,
                                use_lbl_width=len(cfgx2_lbl) < 5))
        print('[harn]-------------')
    print_gtscore()

    #------------

    @ut.argv_flag_dec
    def print_best_rankmat():
        # Prints best ranks
        print('-------------')
        print('RankMat: %s' % testnameid)
        print(' nRows=%r, nCols=%r' % lbld_mat.shape)
        header = (' labled rank matrix: rows=queries, cols=cfgs:')
        #print('\n'.join(qx2_lbl))
        print('\n'.join(cfgx2_lbl))
        #column_list = [row.tolist() for row in lbld_mat[1:].T[1:]]
        column_list = rank_mat.T
        print(ut.make_csv_table(column_list, row_lbls=qaids,
                                column_lbls=column_lbls, header=header,
                                transpose=False,
                                use_lbl_width=len(cfgx2_lbl) < 5))
        #np.set_printoptions(threshold=5000, linewidth=5000, precision=5)
        #with ut.NpPrintOpts(threshold=5000, linewidth=5000, precision=5):
        #print(lbld_mat)
        print('[harn]-------------')
    print_best_rankmat()

    #------------

    @ut.argv_flag_dec
    def print_next_rankmat():
        # Prints nextbest ranks
        print('-------------')
        print('NextRankMat: %s' % testnameid)
        header = (' top false rank matrix: rows=queries, cols=cfgs:')
        #print('\n'.join(qx2_lbl))
        print('\n'.join(cfgx2_lbl))
        #column_list = [row.tolist() for row in lbld_mat[1:].T[1:]]
        column_list = cfgx2_nextbestranks
        print(ut.make_csv_table(column_list, row_lbls=qaids,
                                column_lbls=column_lbls, header=header,
                                transpose=False,
                                use_lbl_width=len(cfgx2_lbl) < 5))
        #np.set_printoptions(threshold=5000, linewidth=5000, precision=5)
        #with ut.NpPrintOpts(threshold=5000, linewidth=5000, precision=5):
        #print(lbld_mat)
        print('[harn]-------------')
    print_next_rankmat()

    #------------

    @ut.argv_flag_dec
    def print_scorediff_mat():
        # Prints nextbest ranks
        print('-------------')
        print('ScoreDiffMat: %s' % testnameid)
        header = (' score difference between top true and top false: rows=queries, cols=cfgs:')
        #print('\n'.join(qx2_lbl))
        print('\n'.join(cfgx2_lbl))
        #column_list = [row.tolist() for row in lbld_mat[1:].T[1:]]
        column_list = cfgx2_scorediffs
        column_type = [float] * len(column_list)
        print(ut.make_csv_table(column_list, row_lbls=qaids,
                                column_lbls=column_lbls,
                                column_type=column_type,
                                header=header,
                                transpose=False,
                                use_lbl_width=len(cfgx2_lbl) < 5))
        #np.set_printoptions(threshold=5000, linewidth=5000, precision=5)
        #with ut.NpPrintOpts(threshold=5000, linewidth=5000, precision=5):
        #print(lbld_mat)
        print('[harn]-------------')
    print_scorediff_mat(alias_flags=['--sdm'])

    #------------
    def jagged_stats_info(arr_, lbl, col_lbls):
        arr = ut.recursive_replace(arr_, np.inf, np.nan)
        # Treat infinite as nan
        stat_dict = ut.get_jagged_stats(arr, use_nan=True, use_sum=True)
        sel_stat_dict, sel_indices = ut.find_interesting_stats(stat_dict, col_lbls)
        sel_col_lbls = ut.list_take(col_lbls, sel_indices)
        statstr_kw   = dict(precision=3, newlines=True, lbl=lbl, align=True)
        stat_str     = ut.get_stats_str(stat_dict=stat_dict, **statstr_kw)
        sel_stat_str = ut.get_stats_str(stat_dict=sel_stat_dict, **statstr_kw)
        sel_stat_str = 'sel_col_lbls = %s' % (ut.list_str(sel_col_lbls),) + '\n' + sel_stat_str
        return stat_str, sel_stat_str

    @ut.argv_flag_dec
    def print_scorediff_mat_stats():
        # Prints nextbest ranks
        print('-------------')
        print('ScoreDiffMatStats: %s' % testnameid)
        print('column_lbls = %r' % (column_lbls,))
        #print('stats = %s' % (ut.get_stats_str(scorediffs_mat.T, precision=3, newlines=True, use_nan=True),))
        #print('sum = %r' % (np.sum(scorediffs_mat, axis=1),))

        #pos_scorediff_mat = vt.zipcompress(scorediffs_mat, istrue_list)
        #neg_scorediff_mat = vt.zipcompress(scorediffs_mat, isfalse_list)

        #score_comparison_mats = [scorediffs_mat, scorefactor_mat, scorelogfactor_mat, scoreexpdiff_mat]
        #score_comparison_mats = [scorediffs_mat]
        score_comparison_mats = [scorediffs_mat, scorefactor_mat]
        # Get the variable names from the stack!
        score_comparison_lbls = list(map(ut.get_varname_from_stack, score_comparison_mats))

        full_statstr_list = []
        sel_statstr_list  = []

        # For each type of score difference get true and false subsets
        for score_comp_mat, lbl in zip(score_comparison_mats, score_comparison_lbls):
            #lbl = ut.get_varname_from_stack(score_comp_mat)
            pos_score_comp_mat = vt.zipcompress(score_comp_mat, istrue_list)
            neg_score_comp_mat = vt.zipcompress(score_comp_mat, isfalse_list)
            # Get statistics on each type of score difference
            full_statstr, sel_statstr         = jagged_stats_info(    score_comp_mat,          lbl, cfgx2_lbl)
            full_pos_statstr, sel_pos_statstr = jagged_stats_info(pos_score_comp_mat, 'pos_' + lbl, cfgx2_lbl)
            full_neg_statstr, sel_neg_statstr = jagged_stats_info(neg_score_comp_mat, 'neg_' + lbl, cfgx2_lbl)
            # Append lists
            full_statstr_list.extend([full_statstr, full_pos_statstr, full_neg_statstr])
            sel_statstr_list.extend([sel_statstr, sel_pos_statstr, sel_neg_statstr])

        #scorediff_str, scorediff_selstr = jagged_stats_info(scorediffs_mat, 'scorediffs_mat', cfgx2_lbl)
        #pos_scorediff_str, pos_scorediff_selstr = jagged_stats_info(pos_scorediff_mat, 'pos_scorediff_mat', cfgx2_lbl)
        #neg_scorediff_str, neg_scorediff_selstr = jagged_stats_info(neg_scorediff_mat, 'neg_scorediff_mat', cfgx2_lbl)

        scorefactor_mat
        scorelogfactor_mat
        scoreexpdiff_mat
        PRINT_FULL_STATS = False
        if PRINT_FULL_STATS:
            for statstr in full_statstr_list:
                print(statstr)

        for statstr in sel_statstr_list:
            print(statstr)

        #print(scorediff_str)
        #print(neg_scorediff_str)
        #print(pos_scorediff_str)

        #print(scorediff_selstr)
        #print(pos_scorediff_selstr)
        #print(neg_scorediff_selstr)
        print('[harn]-------------')
    print_scorediff_mat_stats(alias_flags=['--sdms'])

    @ut.argv_flag_dec
    def print_confusion_stats():
        """
        CommandLine:
            python dev.py --allgt --print-scorediff-mat-stats --print-confusion-stats -t rrvsone_grid
        """
        # Prints nextbest ranks
        print('-------------')
        print('ScoreDiffMatStats: %s' % testnameid)
        print('column_lbls = %r' % (column_lbls,))

        #cfgx2_gt_rawscores  = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_gt_raw_score')
        #cfgx2_gf_rawscores  = ut.get_list_column(cfgx2_cfgresinfo, 'qx2_gf_raw_score')

        gt_rawscores_mat = ut.replace_nones(cfgx2_gt_rawscores, np.nan)
        gf_rawscores_mat = ut.replace_nones(cfgx2_gf_rawscores, np.nan)

        tp_rawscores = vt.zipcompress(gt_rawscores_mat, istrue_list)
        fp_rawscores = vt.zipcompress(gt_rawscores_mat, isfalse_list)
        tn_rawscores = vt.zipcompress(gf_rawscores_mat, istrue_list)
        fn_rawscores = vt.zipcompress(gf_rawscores_mat, isfalse_list)

        tp_rawscores_str, tp_rawscore_statstr = jagged_stats_info(tp_rawscores, 'tp_rawscores', cfgx2_lbl)
        fp_rawscores_str, fp_rawscore_statstr = jagged_stats_info(fp_rawscores, 'fp_rawscores', cfgx2_lbl)
        tn_rawscores_str, tn_rawscore_statstr = jagged_stats_info(tn_rawscores, 'tn_rawscores', cfgx2_lbl)
        fn_rawscores_str, fn_rawscore_statstr = jagged_stats_info(fn_rawscores, 'fn_rawscores', cfgx2_lbl)

        #print(tp_rawscores_str)
        #print(fp_rawscores_str)
        #print(tn_rawscores_str)
        #print(fn_rawscores_str)

        print(tp_rawscore_statstr)
        print(fp_rawscore_statstr)
        print(tn_rawscore_statstr)
        print(fn_rawscore_statstr)

        print('[harn]-------------')
    print_confusion_stats(alias_flags=['--cs'])

    @ut.argv_flag_dec
    def print_diffmat():
        # score differences over configs
        print('-------------')
        print('Diffmat: %s' % testnameid)
        diff_matstr = get_diffmat_str(rank_mat, qaids, nConfig)
        print(diff_matstr)
        print('[harn]-------------')
    print_diffmat()

    #------------
    # Print summary
    print(' --- SUMMARY ---')
    sumstrs = []
    sumstrs.append('')
    sumstrs.append('||===========================')
    sumstrs.append('|| [cfg*] SUMMARY: %s' % testnameid)
    sumstrs.append('||---------------------------')
    sumstrs.append(ut.joins('\n|| ', best_rankscore_summary))
    sumstrs.append('||===========================')
    print('\n' + '\n'.join(sumstrs) + '\n')

    print('To enable all printouts add --print-all to the commandline')


def get_sel_rows_and_cols(qaids, cfg_list, new_hard_qx_list, interesting_qx_list,
                          view_all=ut.get_argflag(('--view-all', '--va')),
                          view_hard=ut.get_argflag(('--view-hard', '--vh')),
                          view_easy=ut.get_argflag(('--view-easy', '--vz')),
                          view_interesting=ut.get_argflag(('--view-interesting', '--vn')),
                          ):
    sel_cols = params.args.sel_cols  # FIXME
    sel_rows = params.args.sel_rows  # FIXME
    sel_cols = [] if sel_cols is None else sel_cols
    sel_rows = [] if sel_rows is None else sel_rows
    #sel_rows = []
    #sel_cols = []
    if ut.NOT_QUIET:
        print('remember to inspect with --sel-rows (-r) and --sel-cols (-c) ')
        print('other options:')
        print('   --vf - view figure dir')
        print('   --va - view all')
        print('   --vh - view hard')
        print('   --ve - view easy')
        print('   --vn - view iNteresting')
    if len(sel_rows) > 0 and len(sel_cols) == 0:
        sel_cols = list(range(len(cfg_list)))
    if len(sel_cols) > 0 and len(sel_rows) == 0:
        sel_rows = list(range(len(qaids)))
    if view_all:
        sel_rows = list(range(len(qaids)))
        sel_cols = list(range(len(cfg_list)))
    if view_hard:
        sel_rows.extend(np.array(new_hard_qx_list).tolist())
        sel_cols.extend(list(range(len(cfg_list))))
    if view_easy:
        new_easy_qx_list = np.setdiff1d(np.arange(len(qaids)), new_hard_qx_list).tolist()
        sel_rows.extend(new_easy_qx_list)
        sel_cols.extend(list(range(len(cfg_list))))
    if view_interesting:
        sel_rows.extend(interesting_qx_list)
        # TODO: grab the best scoring and most interesting configs
        sel_cols.extend(list(range(len(cfg_list))))
    #ut.embed()
    sel_rows = ut.unique_keep_order2(sel_rows)
    sel_cols = ut.unique_keep_order2(sel_cols)
    sel_cols = list(sel_cols)
    sel_rows = list(sel_rows)
    return sel_rows, sel_cols


if __name__ == '__main__':
    """
    CommandLine:
        python -m ibeis.dev.experiment_printres
        python -m ibeis.dev.experiment_printres --allexamples
        python -m ibeis.dev.experiment_printres --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()

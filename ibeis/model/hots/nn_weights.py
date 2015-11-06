# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut
#import six
import numpy as np
#import vtool as vt
import functools
from ibeis.model.hots import scoring
#from ibeis.model.hots import name_scoring
from ibeis.model.hots import hstypes
from ibeis.model.hots import _pipeline_helpers as plh
from six.moves import zip
print, rrr, profile = ut.inject2(__name__, '[nnweight]')


NN_WEIGHT_FUNC_DICT = {}
MISC_WEIGHT_FUNC_DICT = {}
EPS = 1E-8


def _register_nn_normalized_weight_func(func):
    """
    Decorator for weighting functions

    Registers a nearest neighbor normalized weighting
    """
    global NN_WEIGHT_FUNC_DICT
    filtkey = ut.get_funcname(func).replace('_fn', '').lower()
    if ut.VERYVERBOSE:
        print('[nn_weights] registering norm func: %r' % (filtkey,))
    filtfunc = functools.partial(nn_normalized_weight, func)
    NN_WEIGHT_FUNC_DICT[filtkey] = filtfunc
    return func


def _register_nn_simple_weight_func(func):
    filtkey = ut.get_funcname(func).replace('_match_weighter', '').lower()
    if ut.VERYVERBOSE:
        print('[nn_weights] registering simple func: %r' % (filtkey,))
    NN_WEIGHT_FUNC_DICT[filtkey] = func
    return func


def _register_misc_weight_func(func):
    filtkey = ut.get_funcname(func).replace('_match_weighter', '').lower()
    if ut.VERYVERBOSE:
        print('[nn_weights] registering simple func: %r' % (filtkey,))
    MISC_WEIGHT_FUNC_DICT[filtkey] = func
    return func


#def componentwise_uint8_dot(qfx2_qvec, qfx2_dvec):
#    """ a dot product is a componentwise multiplication of
#    two vector and then a sum. Do that for arbitary vectors.
#    Remember to cast uint8 to float32 and then divide by 255**2.
#    BUT THESE ARE SIFT DESCRIPTORS WHICH USE THE SMALL UINT8 TRICK
#    DIVIDE BY 512**2 instead
#    """
#    arr1 = qfx2_qvec.astype(hstypes.FS_DTYPE)
#    arr2 = qfx2_dvec.astype(hstypes.FS_DTYPE)
#    assert qfx2_qvec.dtype.type == np.uint8, 'must have normalized sift descriptors here'
#    cosangle = vt.componentwise_dot(arr1, arr2) / hstypes.PSEUDO_UINT8_MAX_SQRD
#    return cosangle


@_register_nn_simple_weight_func
def const_match_weighter(nns_list, nnvalid0_list, qreq_):
    """
    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> tup = plh.testdata_pre_weight_neighbors('PZ_MTEST')
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> constvote_weight_list = borda_match_weighter(nns_list, nnvalid0_list, qreq_)
        >>> result = ('constvote_weight_list = %s' % (str(constvote_weight_list),))
        >>> print(result)
    """
    constvote_weight_list = []
    K = qreq_.qparams.K
    for nns in (nns_list):
        (qfx2_idx, qfx2_dist) = nns
        qfx2_constvote = np.ones((len(qfx2_idx), K), dtype=np.float)
        constvote_weight_list.append(qfx2_constvote)
    return constvote_weight_list


@_register_nn_simple_weight_func
def borda_match_weighter(nns_list, nnvalid0_list, qreq_):
    r"""
    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> tup = plh.testdata_pre_weight_neighbors('PZ_MTEST')
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> bordavote_weight_list = borda_match_weighter(nns_list, nnvalid0_list, qreq_)
        >>> result = ('bordavote_weight_list = %s' % (str(bordavote_weight_list),))
        >>> print(result)
    """
    bordavote_weight_list = []
    K = qreq_.qparams.K
    _branks = np.arange(1, K + 1, dtype=np.float)[::-1]
    bordavote_weight_list = [
        np.tile(_branks, (len(qfx2_idx), 1))
        for (qfx2_idx, qfx2_dist) in nns_list
    ]
    return bordavote_weight_list


@_register_nn_simple_weight_func
def cos_match_weighter(nns_list, nnvalid0_list, qreq_):
    r"""

    CommandLine:
        python -m ibeis.model.hots.nn_weights --test-cos_match_weighter

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> from ibeis.model.hots import nn_weights
        >>> tup = plh.testdata_pre_weight_neighbors('PZ_MTEST', cfgdict=dict(cos_on=True, K=5, Knorm=5))
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> assert qreq_.qparams.cos_on, 'bug setting custom params cos_weight'
        >>> cos_weight_list = nn_weights.cos_match_weighter(nns_list, nnvalid0_list, qreq_)

    Ignore:
        qnid = ibs.get_annot_name_rowids(qaid)
        qfx2_nids = ibs.get_annot_name_rowids(qreq_.indexer.get_nn_aids(qfx2_idx.T[0:K].T))
        # remove first match
        qfx2_nids_ = qfx2_nids.T[1:].T
        qfx2_cos_  = qfx2_cos.T[1:].T
        # flags of unverified 'correct' matches
        qfx2_samename = qfx2_nids_ == qnid
        for k in [1, None]:
            for alpha in [.01, .1, 1, 3, 10, 20, 50]:
                print('-------')
                print('alpha = %r' % alpha)
                print('k = %r' % k)
                qfx2_cosweight = np.multiply(np.sign(qfx2_cos_), np.power(qfx2_cos_, alpha))
                if k is None:
                    qfx2_weight = qfx2_cosweight
                    flag = qfx2_samename
                else:
                    qfx2_weight = qfx2_cosweight.T[0:k].T
                    flag = qfx2_samename.T[0:k].T
                #print(qfx2_weight)
                #print(flag)
                good_stats_ = ut.get_stats(qfx2_weight[flag])
                bad_stats_ = ut.get_stats(qfx2_weight[~flag])
                print('good_matches = ' + ut.dict_str(good_stats_))
                print('bad_matchees = ' + ut.dict_str(bad_stats_))
                print('diff_mean = ' + str(good_stats_['mean'] - bad_stats_['mean']))
    """
    Knorm = qreq_.qparams.Knorm
    cos_weight_list = []
    qaid_list = qreq_.get_internal_qaids()
    qconfig2_ = qreq_.get_internal_query_config2()
    # Database feature index to chip index
    for qaid, nns in zip(qaid_list, nns_list):
        (qfx2_idx, qfx2_dist) = nns
        qfx2_qvec = qreq_.ibs.get_annot_vecs(qaid, config2_=qconfig2_)[np.newaxis, :, :]
        # database forground weights
        # avoid using K due to its more dynamic nature by using -Knorm
        qfx2_dvec = qreq_.indexer.get_nn_vecs(qfx2_idx.T[:-Knorm])
        # Component-wise dot product + selectivity function
        alpha = 3.0
        qfx2_cosweight = scoring.sift_selectivity_score(qfx2_qvec, qfx2_dvec, alpha)
        cos_weight_list.append(qfx2_cosweight)
    return cos_weight_list


@_register_nn_simple_weight_func
def fg_match_weighter(nns_list, nnvalid0_list, qreq_):
    r"""
    foreground feature match weighting

    CommandLine:
        python -m ibeis.model.hots.nn_weights --exec-fg_match_weighter

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> tup = plh.testdata_pre_weight_neighbors('PZ_MTEST')
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> print(ut.dict_str(qreq_.qparams.__dict__, sorted_=True))
        >>> assert qreq_.qparams.fg_on == True, 'bug setting custom params fg_on'
        >>> fgvotes_list = fg_match_weighter(nns_list, nnvalid0_list, qreq_)
        >>> print('fgvotes_list = %r' % (fgvotes_list,))
    """
    Knorm = qreq_.qparams.Knorm
    qaid_list = qreq_.get_internal_qaids()
    config2_ = qreq_.get_internal_query_config2()
    # Database feature index to chip index
    fgvotes_list = []
    for qaid, nns in zip(qaid_list, nns_list):
        (qfx2_idx, qfx2_dist) = nns
        # database forground weights
        qfx2_dfgw = qreq_.indexer.get_nn_fgws(qfx2_idx.T[0:-Knorm].T)
        # query forground weights
        qfx2_qfgw = qreq_.ibs.get_annot_fgweights([qaid], ensure=False, config2_=config2_)[0]
        # feature match forground weight
        qfx2_fgvote_weight = np.sqrt(qfx2_qfgw[:, None] * qfx2_dfgw)
        fgvotes_list.append(qfx2_fgvote_weight)
    return fgvotes_list


@_register_misc_weight_func
def distinctiveness_match_weighter(qreq_):
    """
    TODO: finish intergration

    Example:
        >>> # SLOW_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> from ibeis.model.hots import nn_weights
        >>> tup = plh.testdata_pre_weight_neighbors('PZ_MTEST', codename='vsone_dist_extern_distinctiveness')
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
    """
    dstcnvs_normer = qreq_.dstcnvs_normer
    assert dstcnvs_normer is not None
    qaid_list = qreq_.get_external_qaids()
    vecs_list = qreq_.ibs.get_annot_vecs(qaid_list, config2_=qreq_.get_internal_query_config2())
    dstcvs_list = []
    for vecs in vecs_list:
        qfx2_vec = vecs
        dstcvs = dstcnvs_normer.get_distinctiveness(qfx2_vec)
        dstcvs_list.append(dstcvs)
    return dstcvs_list


def nn_normalized_weight(normweight_fn, nns_list, nnvalid0_list, qreq_):
    """
    Generic function to weight nearest neighbors

    ratio, lnbnn, and other nearest neighbor based functions use this

    Args:
        normweight_fn (func): chosen weight function e.g. lnbnn
        nns_list (dict): query descriptor nearest neighbors and distances. (qfx2_nnx, qfx2_dist)
        qreq_ (QueryRequest): hyper-parameters

    Returns:
        list: weights_list

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> from ibeis.model.hots import nn_weights
        >>> tup = plh.testdata_pre_weight_neighbors('PZ_MTEST')
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> normweight_fn = lnbnn_fn
        >>> weights_list1 = nn_weights.nn_normalized_weight(normweight_fn, nns_list, nnvalid0_list, qreq_)
        >>> weights1 = weights_list1[0]
        >>> nn_normonly_weight = nn_weights.NN_WEIGHT_FUNC_DICT['lnbnn']
        >>> weights_list2 = nn_normonly_weight(nns_list, nnvalid0_list, qreq_)
        >>> weights2 = weights_list2[0]
        >>> assert np.all(weights1 == weights2)
        >>> ut.assert_inbounds(weights1.sum(), 200, 300)

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> from ibeis.model.hots import nn_weights
        >>> tup = plh.testdata_pre_weight_neighbors('PZ_MTEST')
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> normweight_fn = ratio_fn
        >>> weights_list1 = nn_weights.nn_normalized_weight(normweight_fn, nns_list, nnvalid0_list, qreq_)
        >>> weights1 = weights_list1[0]
        >>> nn_normonly_weight = nn_weights.NN_WEIGHT_FUNC_DICT['ratio']
        >>> weights_list2 = nn_normonly_weight(nns_list, nnvalid0_list, qreq_)
        >>> weights2 = weights_list2[0]
        >>> assert np.all(weights1 == weights2)
        >>> ut.assert_inbounds(weights1.sum(), 2700, 4000)

    Ignore:
        #from ibeis.model.hots import neighbor_index as hsnbrx
        #nnindexer = hsnbrx.request_ibeis_nnindexer(qreq_)
    """
    Knorm = qreq_.qparams.Knorm
    normalizer_rule  = qreq_.qparams.normalizer_rule
    # Database feature index to chip index
    qaid_list = qreq_.get_internal_qaids()
    weight_list = [
        apply_normweight(
            normweight_fn, qaid, qfx2_idx, qfx2_dist, normalizer_rule, Knorm, qreq_)
        for qaid, (qfx2_idx, qfx2_dist) in zip(qaid_list, nns_list)
    ]
    return weight_list


def apply_normweight(normweight_fn, qaid, qfx2_idx, qfx2_dist, normalizer_rule,
                     Knorm, qreq_):
    """ helper applies the normalized weight function to one query annotation

    Args:
        normweight_fn (func):  chosen weight function e.g. lnbnn
        qaid (int):  query annotation id
        qfx2_idx (ndarray[int32_t, ndims=2]):  mapping from query feature index to db neighbor index
        qfx2_dist (ndarray):  mapping from query feature index to dist
        normalizer_rule (str):
        Knorm (int):
        qreq_ (QueryRequest):  query request object with hyper-parameters

    Returns:
        ndarray: qfx2_normweight

    CommandLine:
        python -m ibeis.model.hots.nn_weights --test-apply_normweight

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> from ibeis.model.hots import nn_weights
        >>> cfgdict = {'K':10, 'Knorm': 10, 'normalizer_rule': 'name'}
        >>> tup = plh.testdata_pre_weight_neighbors(cfgdict=cfgdict)
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> qaid = qreq_.get_external_qaids()[0]
        >>> Knorm = qreq_.qparams.Knorm
        >>> normweight_fn = lnbnn_fn
        >>> normalizer_rule  = qreq_.qparams.normalizer_rule
        >>> (qfx2_idx, qfx2_dist) = nns_list[0]
        >>> qfx2_normweight = nn_weights.apply_normweight(normweight_fn, qaid, qfx2_idx,
        ...         qfx2_dist, normalizer_rule, Knorm, qreq_)
        >>> ut.assert_inbounds(qfx2_normweight.sum(), 800, 950)
    """
    K = len(qfx2_idx.T) - Knorm
    assert K > 0, 'K cannot be 0'
    qfx2_nndist = qfx2_dist.T[0:K].T
    if normalizer_rule == 'last':
        # Normalizers for 'last' normalizer_rule
        qfx2_normk = np.zeros(len(qfx2_dist), hstypes.FK_DTYPE) + (K + Knorm - 1)
    elif normalizer_rule == 'name':
        # Normalizers for 'name' normalizer_rule
        qfx2_normk = get_name_normalizers(qaid, qreq_, Knorm, qfx2_idx)
    elif normalizer_rule == 'external':
        pass
    else:
        raise NotImplementedError('[nn_weights] no normalizer_rule=%r' % normalizer_rule)
    qfx2_normdist = np.array([dists[normk]
                              for (dists, normk) in zip(qfx2_dist, qfx2_normk)])
    qfx2_normdist.shape = (len(qfx2_idx), 1)
    vdist = qfx2_nndist    # voting distance
    ndist = qfx2_normdist  # normalizer distance
    qfx2_normweight = normweight_fn(vdist, ndist)
    return qfx2_normweight


def get_name_normalizers(qaid, qreq_, Knorm, qfx2_idx):
    """ helper normalizers for 'name' normalizer_rule

    Args:
        qaid (int): query annotation id
        qreq_ (QueryRequest): hyper-parameters
        Knorm (int):
        qfx2_idx (ndarray):

    Returns:
        ndarray : qfx2_normk

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> from ibeis.model.hots import nn_weights
        >>> cfgdict = {'K':10, 'Knorm': 10, 'normalizer_rule': 'name'}
        >>> tup = plh.testdata_pre_weight_neighbors(cfgdict=cfgdict)
        >>> ibs, qreq_, nns_list, nnvalid0_list = tup
        >>> Knorm = qreq_.qparams.Knorm
        >>> (qfx2_idx, qfx2_dist) = nns_list[0]
        >>> qaid = qreq_.get_external_qaids()[0]
        >>> qfx2_normk = get_name_normalizers(qaid, qreq_, Knorm, qfx2_idx)
    """
    assert Knorm == qreq_.qparams.Knorm, 'inconsistency in qparams'
    # Get the top names you do not want your normalizer to be from
    qnid = qreq_.ibs.get_annot_name_rowids(qaid)
    K = len(qfx2_idx.T) - Knorm
    assert K > 0, 'K cannot be 0'
    # Get the 0th - Kth matching neighbors
    qfx2_topidx = qfx2_idx.T[0:K].T
    # Get tke Kth - KNth normalizing neighbors
    qfx2_normidx = qfx2_idx.T[-Knorm:].T
    # Apply temporary uniquish name
    qfx2_topaid  = qreq_.indexer.get_nn_aids(qfx2_topidx)
    qfx2_normaid = qreq_.indexer.get_nn_aids(qfx2_normidx)
    qfx2_topnid  = qreq_.ibs.get_annot_name_rowids(qfx2_topaid)
    qfx2_normnid = qreq_.ibs.get_annot_name_rowids(qfx2_normaid)
    # Inspect the potential normalizers
    qfx2_selnorm = mark_name_valid_normalizers(qnid, qfx2_topnid, qfx2_normnid)
    qfx2_normk = qfx2_selnorm + (K + Knorm)  # convert form negative to pos indexes
    return qfx2_normk


def mark_name_valid_normalizers(qnid, qfx2_topnid, qfx2_normnid):
    """ Helper func that allows matches only to the first result for a name

    Each query feature finds its K matches and Kn normalizing matches. These are the
    candidates from which it can choose a set of matches and a single normalizer.

    A normalizer is marked as invalid if it belongs to a name that was also in its
    feature's candidate matching set.

    Args:
        qfx2_topnid (ndarray): marks the names a feature matches
        qfx2_normnid (ndarray): marks the names of the feature normalizers
        qnid (int): query name id

    Returns:
        qfx2_selnorm - index of the selected normalizer for each query feature

    CommandLine:
        python -m ibeis.model.hots.nn_weights --exec-mark_name_valid_normalizers

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> qnid = 1
        >>> qfx2_topnid = np.array([[1, 1, 1, 1, 1],
        ...                         [1, 2, 1, 1, 1],
        ...                         [1, 2, 2, 3, 1],
        ...                         [5, 8, 9, 8, 8],
        ...                         [5, 8, 9, 8, 8],
        ...                         [6, 6, 9, 6, 8],
        ...                         [5, 8, 6, 6, 6],
        ...                         [1, 2, 8, 6, 6]], dtype=np.int32)
        >>> qfx2_normnid = np.array([[ 1, 1, 1],
        ...                          [ 2, 3, 1],
        ...                          [ 2, 3, 1],
        ...                          [ 6, 6, 6],
        ...                          [ 6, 6, 8],
        ...                          [ 2, 6, 6],
        ...                          [ 6, 6, 1],
        ...                          [ 4, 4, 9]], dtype=np.int32)
        >>> qfx2_selnorm = mark_name_valid_normalizers(qnid, qfx2_topnid, qfx2_normnid)
        >>> K = len(qfx2_topnid.T)
        >>> Knorm = len(qfx2_normnid.T)
        >>> qfx2_normk_ = qfx2_selnorm + (Knorm)  # convert form negative to pos indexes
        >>> result = str(qfx2_normk_)
        >>> print(result)
        [2 1 2 0 0 0 2 0]

    Ignore:
        print(ut.doctest_repr(qfx2_normnid, 'qfx2_normnid', verbose=False))
        print(ut.doctest_repr(qfx2_topnid, 'qfx2_topnid', verbose=False))
    """
    # The normalizer should be from a name that is not in any of the top
    # matches if possible. If not possible it should be from the name with the
    # highest k value.

    #old_qfx2_invalid = vt.compare_matrix_columns(qfx2_normnid, qfx2_topnid, comp_op=np.equal, logic_op=np.logical_or)
    # Find the positions in the normalizers that could be valid
    # (assumes Knorm > 1)
    # IE positions in qfx2_normnid that appear anywhere in the corresponding
    # row of qfx2_topnid
    # TODO?: warn if any([np.any(flags) for flags in qfx2_invalid]), 'Normalizers are potential matches. Increase Knorm'

    #qfx2_invalid = np.logical_or.reduce([col1[:, None] == qfx2_normnid for col1 in qfx2_topnid.T])
    #qfx2_valid = np.logical_not(qfx2_invalid)
    qfx2_valid = np.logical_and.reduce([col1[:, None] != qfx2_normnid for col1 in qfx2_topnid.T])

    #if qnid is not None:
    # Mark self as invalid, if given that information
    qfx2_valid = np.logical_and(qfx2_normnid != qnid, qfx2_valid)

    # For each query feature find its best normalizer (using negative indices)
    Knorm = qfx2_normnid.shape[1]
    qfx2_validxs = [np.nonzero(normrow)[0] for normrow in qfx2_valid]
    qfx2_selnorm = np.array([validxs[0] - Knorm if len(validxs) != 0 else -1
                             for validxs in qfx2_validxs], hstypes.FK_DTYPE)
    return qfx2_selnorm


@_register_nn_normalized_weight_func
def lnbnn_fn(vdist, ndist):
    """
    Locale Naive Bayes Nearest Neighbor weighting

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> vdist, ndist = testdata_vn_dists()
        >>> out = lnbnn_fn(vdist, ndist)
        >>> result = ut.hz_str('lnbnn  = ', ut.repr2(out, precision=2))
        >>> print(result)
        lnbnn  = np.array([[ 0.62,  0.22,  0.03],
                           [ 0.35,  0.22,  0.01],
                           [ 0.87,  0.58,  0.27],
                           [ 0.67,  0.42,  0.25],
                           [ 0.59,  0.3 ,  0.27]])
    """
    return (ndist - vdist)


@_register_nn_normalized_weight_func
def ratio_fn(vdist, ndist):
    r"""
    Args:
        vdist (ndarray): voting array
        ndist (ndarray): normalizing array

    Returns:
        ndarray: out

    Example1:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> vdist, ndist = testdata_vn_dists()
        >>> out = ratio_fn(vdist, ndist)
        >>> result = ut.hz_str('ratio = ', ut.repr2(out, precision=2))
        >>> print(result)
        ratio = np.array([[ 0.  ,  0.65,  0.95],
                          [ 0.33,  0.58,  0.98],
                          [ 0.13,  0.42,  0.73],
                          [ 0.15,  0.47,  0.68],
                          [ 0.23,  0.61,  0.65]])
    """
    return np.divide(vdist, ndist)


@_register_nn_normalized_weight_func
def bar_l2_fn(vdist, ndist):
    """
    The feature weight is (1 - the euclidian distance
    between the features). The normalizers are unused.

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> vdist, ndist = testdata_vn_dists()
        >>> out = bar_l2_fn(vdist, ndist)
        >>> result = ut.hz_str('barl2  = ', ut.repr2(out, precision=2))
        >>> print(result)
        barl2  = np.array([[ 1.  ,  0.6 ,  0.41],
                           [ 0.83,  0.7 ,  0.49],
                           [ 0.87,  0.58,  0.27],
                           [ 0.88,  0.63,  0.46],
                           [ 0.82,  0.53,  0.5 ]])
    """
    return 1.0 - vdist


@_register_nn_normalized_weight_func
def loglnbnn_fn(vdist, ndist):
    """
    Ignore:
        import vtool as vt
        vt.check_expr_eq('log(d) - log(n)', 'log(d / n)')   # True
        vt.check_expr_eq('log(d) / log(n)', 'log(d - n)')

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> vdist, ndist = testdata_vn_dists()
        >>> out = loglnbnn_fn(vdist, ndist)
        >>> result = ut.hz_str('loglnbnn  = ', ut.repr2(out, precision=2))
        >>> print(result)
        loglnbnn  = np.array([[ 0.48,  0.2 ,  0.03],
                              [ 0.3 ,  0.2 ,  0.01],
                              [ 0.63,  0.46,  0.24],
                              [ 0.51,  0.35,  0.22],
                              [ 0.46,  0.26,  0.24]])
    """
    return np.log(ndist - vdist + 1.0)


@_register_nn_normalized_weight_func
def logratio_fn(vdist, ndist):
    """
    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> vdist, ndist = testdata_vn_dists()
        >>> out = normonly_fn(vdist, ndist)
        >>> result = ut.repr2(out)
        >>> print(result)
        np.array([[ 0.62,  0.62,  0.62],
                  [ 0.52,  0.52,  0.52],
                  [ 1.  ,  1.  ,  1.  ],
                  [ 0.79,  0.79,  0.79],
                  [ 0.77,  0.77,  0.77]])
    """
    return np.log(np.divide(ndist, vdist + EPS) + 1.0)


@_register_nn_normalized_weight_func
def normonly_fn(vdist, ndist):
    """
    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> vdist, ndist = testdata_vn_dists()
        >>> out = normonly_fn(vdist, ndist)
        >>> result = ut.repr2(out)
        >>> print(result)
        np.array([[ 0.62,  0.62,  0.62],
                  [ 0.52,  0.52,  0.52],
                  [ 1.  ,  1.  ,  1.  ],
                  [ 0.79,  0.79,  0.79],
                  [ 0.77,  0.77,  0.77]])
    """
    return np.tile(ndist[:, 0:1], (1, vdist.shape[1]))
    #return ndist[None, 0:1]


def testdata_vn_dists(nfeats=5, K=3):
    """
    Test voting and normalizing distances

    Returns:
        tuple : (vdist, ndist) - test voting distances and normalizer distances

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.model.hots.nn_weights import *  # NOQA
        >>> vdist, ndist = testdata_vn_dists()
        >>> print(ut.hz_str('vdist = ', ut.repr2(vdist)))
        >>> print(ut.hz_str('ndist = ', ut.repr2(ndist)))
        vdist = np.array([[ 0.  ,  0.4 ,  0.59],
                          [ 0.17,  0.3 ,  0.51],
                          [ 0.13,  0.42,  0.73],
                          [ 0.12,  0.37,  0.54],
                          [ 0.18,  0.47,  0.5 ]])
        ndist = np.array([[ 0.62],
                          [ 0.52],
                          [ 1.  ],
                          [ 0.79],
                          [ 0.77]])
    """
    def make_precise(dist):
        prec = 100
        dist = ((prec * dist).astype(np.uint8) / prec)
        dist = dist.astype(hstypes.FS_DTYPE)
        return dist
    rng = np.random.RandomState(0)
    vdist = rng.rand(nfeats, K)
    ndist = rng.rand(nfeats, 1)
    # Ensure distance increases
    vdist = vdist.cumsum(axis=1)
    ndist = (ndist.T + vdist.max(axis=1)).T
    Z = ndist.max()
    vdist = make_precise(vdist / Z)
    ndist = make_precise(ndist / Z)
    vdist[0][0] = 0
    return vdist, ndist


#@_register_nn_normalized_weight_func
#def dist_fn(vdist, ndist):
#    """ the euclidian distance between the features """
#    return vdist


#@_register_nn_simple_weight_func
def gravity_match_weighter(nns_list, nnvalid0_list, qreq_):
    raise NotImplementedError('have not finished gv weighting')
    #qfx2_nnkpts = qreq_.indexer.get_nn_kpts(qfx2_nnidx)
    #qfx2_nnori = ktool.get_oris(qfx2_nnkpts)
    #qfx2_kpts  = qreq_.ibs.get_annot_kpts(qaid, config2_=qreq_.get_internal_query_config2())  # FIXME: Highly inefficient
    #qfx2_oris  = ktool.get_oris(qfx2_kpts)
    ## Get the orientation distance
    #qfx2_oridist = vt.rowwise_oridist(qfx2_nnori, qfx2_oris)
    ## Normalize into a weight (close orientations are 1, far are 0)
    #qfx2_gvweight = (TAU - qfx2_oridist) / TAU
    ## Apply gravity vector weight to the score
    #qfx2_score *= qfx2_gvweight


def test_all_normalized_weights():
    """
    CommandLine:
        python -m ibeis.model.hots.nn_weights --exec-test_all_normalized_weights

    Example:
        >>> # ENABLE_DOCTEST
        >>> test_all_normalized_weights()
    """
    from ibeis.model.hots import nn_weights
    import six
    ibs, qreq_, nns_list, nnvalid0_list = plh.testdata_pre_weight_neighbors()
    qaid = qreq_.get_external_qaids()[0]

    def test_weight_fn(nn_weight, nns_list, qreq_, qaid):
        from ibeis.model.hots import nn_weights
        #----
        normweight_fn = nn_weights.__dict__[nn_weight + '_fn']
        weight_list1 = nn_weights.nn_normalized_weight(normweight_fn, nns_list, nnvalid0_list, qreq_)
        weights1 = weight_list1[0]
        #---
        # test NN_WEIGHT_FUNC_DICT
        #---
        nn_normonly_weight = nn_weights.NN_WEIGHT_FUNC_DICT[nn_weight]
        weight_list2 = nn_normonly_weight(nns_list, nnvalid0_list, qreq_)
        weights2 = weight_list2[0]
        assert np.all(weights1 == weights2)
        print(nn_weight + ' passed')

    for nn_weight in six.iterkeys(nn_weights.NN_WEIGHT_FUNC_DICT):
        normweight_key = nn_weight + '_fn'
        if normweight_key not in nn_weights.__dict__:
            continue
        test_weight_fn(nn_weight, nns_list, qreq_, qaid)


if __name__ == '__main__':
    """
    python -m ibeis.model.hots.nn_weights --allexamples
    python -m ibeis.model.hots.nn_weights
    """
    import multiprocessing
    multiprocessing.freeze_support()
    import utool as ut  # NOQA
    ut.doctest_funcs()

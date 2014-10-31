from __future__ import absolute_import, division, print_function
import six
import utool as ut
from ibeis import constants


class SHORTNAMES(object):
    RVEC = 'residual'
    #RVEC = 'rvec'
    FEAT = 'feat'

depends_map = {
    'annot': None,
    'chip': 'annot',
    'feat': 'chip',
    'featweight': 'feat',
    SHORTNAMES.RVEC: SHORTNAMES.FEAT
}

# shortened tablenames
tablename2_tbl = {
    constants.ANNOTATION_TABLE     : 'annot',
    constants.CHIP_TABLE           : 'chip',
    constants.FEATURE_TABLE        : 'feat',
    constants.FEATURE_WEIGHT_TABLE : 'featweight',
    constants.RESIDUAL_TABLE       : SHORTNAMES.RVEC,
}


tbl2_TABLE = {
    'annot'      : 'ANNOTATION_TABLE',
    'chip'       : 'CHIP_TABLE',
    'feat'       : 'FEATURE_TABLE',
    'featweight' : 'FEATURE_WEIGHT_TABLE',
    SHORTNAMES.RVEC  : 'RESIDUAL_TABLE',
}


variable_aliases = {
    #'chip_rowid_list': 'cid_list',
    #'annot_rowid_list': 'aid_list',
    #'feature_rowid_list': 'fid_list',
    'chip_rowid': 'cid',
    'annot_rowid': 'aid',
    'feat_rowid': 'fid',
    'num_feats': 'nFeats',
    'forground_weight': 'fgweight',
    'keypoints': 'kpts',
    'vectors': 'vecs',
}


get_child_config_rowid_template = ut.codeblock(
    '''
    def get_{child}_config_rowid({self}):
        """
        returns config_rowid of the current configuration

        AUTOGENERATED ON {timestamp}
        """
        {child}_cfg_suffix = {self}.cfg.{child}_cfg.get_cfgstr()
        cfgsuffix_list = [{child}_cfg_suffix]
        {child}_cfg_rowid = {self}.add_config(cfgsuffix_list)
    '''
)


add_dependent_child_stub_template = ut.codeblock(
    '''
    def add_{parent}_{child}({self}, {parent}_rowid_list, config_rowid=None):
        """
        Adds / ensures / computes a dependent property

        returns config_rowid of the current configuration

        AUTOGENERATED ON {timestamp}
        """
        raise NotImplementedError('this code is a stub, you must populate it')
        if config_rowid is None:
            config_rowid = {self}.get_{child}_config_rowid()
        {child}_rowid_list = ibs.get_{parent}_{child}_rowids(
            {parent}_rowid_list, config_rowid=config_rowid, ensure=False)
        dirty_{parent}_rowid_list = utool.get_dirty_items({parent}_rowid_list, {child}_rowid_list)
        if len(dirty_{parent}_rowid_list) > 0:
            if utool.VERBOSE:
                print('[ibs] adding %d / %d {child}' % (len(dirty_{parent}_rowid_list), len({parent}_rowid_list)))

            # params_iter = preproc_{child}.add_{child}_params_gen(ibs, dirty_{parent}_rowid_list)
            colnames = {child_colnames}
            #'chip_rowid', 'feature_num_feats', 'feature_keypoints', 'feature_vecs', 'config_rowid',)
            get_rowid_from_superkey = partial(ibs.get_{parent}_{child}_rowids, ensure=False)
            {child}_rowid_list = ibs.dbcache.add_cleanly({TABLE}, colnames, params_iter, get_rowid_from_superkey)
        return {child}_rowid_list
    '''
)

#where_clause = {PARENT}_ROWID + '=? AND ' + CONFIG_ROWID + '=?'
# Template for a child rowid that depends on a parent rowid + a config
get_configed_child_rowids_template = ut.codeblock(
    '''
    def get_{parent}_{child}_rowids({self}, {parent}_rowid_list,
                                      config_rowid=None, all_configs=False,
                                      ensure=True, eager=True,
                                      num_params=None):
        """
        get_{parent}_{child}_rowids

        get {child} rowids of {parent} under the current state configuration

        AUTOGENERATED ON {timestamp}

        Args:
            {parent}_rowid_list (list):

        Returns:
            list: {child}_rowid_list
        """
        if ensure:
            {self}.add_{child}s({parent}_rowid_list)
        if config_rowid is None:
            config_rowid = {self}.get_{child}_config_rowid()
        colnames = ({CHILD}_ROWID,)
        if all_configs:
            config_rowid = {self}.{sqldb}.get(
                {TABLE}, colnames, {parent}_rowid_list,
                id_colname={PARENT}_ROWID, eager=eager, num_params=num_params)
        else:
            config_rowid = {self}.get_{child}_config_rowid()
            # This template could be smoothed out a bit by sql controller
            andwhere_colnames = [{PARENT}_ROWID, CONFIG_ROWID]
            params_iter = (({parent}_rowid, config_rowid,) for {parent}_rowid in {parent}_rowid_list)
            {child}_rowid_list = {self}.{sqldb}.get_where2(
                {TABLE}, colnames, params_iter, andwhere_colnames, eager=eager,
                num_params=num_params)
        return {child}_rowid_list
    ''')

get_dependency_template = ut.codeblock(
    '''
    def get_{parent}_{col}({self}, {parent}_rowid_list,
                                 config_rowid=None):
        """
        get_{parent}_{col}

        get {col} data of the {parent} table using the {child} table

        AUTOGENERATED ON {timestamp}

        Args:
            {parent}_rowid_list (list):

        Returns:
            list: {col}_list
        """
        {child}_rowid_list = {self}.get_{parent}_{child}_rowids({parent}_rowid_list)
        {col}_list = {self}.get_{child}_{col}({child}_rowid_list, config_rowid=config_rowid)
        return {col}_list
    ''')

get_column_template = ut.codeblock(
    '''
    def get_{tbl}_{col}({self}, {tbl}_rowid_list):
        """
        get_{tbl}_{col}

        get {col} column data from the {tbl} table

        AUTOGENERATED ON {timestamp}

        Args:
            {tbl}_rowid_list (list):

        Returns:
            list: {col}_list
        """
        params_iter = (({tbl}_rowid,) for {tbl}_rowid in {tbl}_rowid_list)
        colnames = ({COLNAME},)
        {col}_list = {self}.dbcache.get({TABLE}, colnames, params_iter)
        return {col}_list
    ''')


#def test():
#    from ibeis.control.templates import *  # NOQA

def build_depends_path(child):
    parent = depends_map[child]
    if parent is not None:
        return build_depends_path(parent) + [child]
    else:
        return [child]
    #depends_list = ['annot', 'chip', 'feat', 'featweight']


def singular_string(str_):
    return str_[:-1] if str_.endswith('s') else str_


def colname2_col(colname, tablename):
    # col is a short alias for colname
    col = colname.replace(singular_string(tablename) + '_', '')
    return col


def build_dependent_controller_funcs(tablename, other_colnames, all_colnames, sqldb_):
    child = tablename2_tbl[tablename]
    depends_list = build_depends_path(child)

    CONSTANT_COLNAMES = []

    fmtdict = {
        'self': 'ibs',
        'timestamp': ut.get_timestamp('printable'),
        #'parent': None,
        #'child':  None,
        #'CHILD':  None,
        #'COLNAME': None,  # 'FGWEIGHTS',
        #'parent_rowid_list': 'aid_list',
        'sqldb': sqldb_,
        #'TABLE': None,
        #'FEATURE_TABLE',
    }
    func_list = []

    def format_controller_func(func_code):
        STRIP_DOCSTR = False
        USE_SHORTNAMES = False

        if STRIP_DOCSTR:
            # might not always work the newline is a hack to remove
            # that dumb blank line
            func_code = ut.regex_replace('""".*"""\n    ', '', func_code)
        #func_code = ut.regex_replace('\'[^\']*\'', '', func_code)
        if USE_SHORTNAMES:
            # Cannot do this until quoted strings are preserved
            # This should hack it in
            def preserve_quoted_str(quoted_str):
                #print(quoted_str)
                return '\'' + '_'.join(list(quoted_str[1:-1])) + '\''
            def unpreserve_quoted_str(quoted_str):
                #print(quoted_str)
                return '\'' + ''.join(list(quoted_str[1:-1])[::2]) + '\''
            func_code = ut.modify_quoted_strs(func_code, preserve_quoted_str)
            for varname, alias in six.iteritems(variable_aliases):
                func_code = func_code.replace(varname, alias)
            func_code = ut.modify_quoted_strs(func_code, unpreserve_quoted_str)
        func_code = ut.autofix_codeblock(func_code)
        func_code = ut.indent(func_code)
        return func_code

    def append_func(func_code):
        func_code = format_controller_func(func_code)
        func_list.append(func_code)

    func_list.append('    # --- %s ROWIDS --- ' % (tablename.upper()))

    for parent, child in ut.itertwo(depends_list):
        fmtdict['parent'] = parent
        fmtdict['child'] = child
        fmtdict['PARENT'] = parent.upper()
        fmtdict['CHILD'] = child.upper()
        fmtdict['TABLE'] = tbl2_TABLE[child]  # tblname1_TABLE[child]
        append_func(get_configed_child_rowids_template.format(**fmtdict))

    func_list.append('    # --- %s DEPENDANT PROPERTIES --- ' % (tablename.upper()))

    CONSTANT_COLNAMES.extend(other_colnames)

    for colname in other_colnames:
        col = colname2_col(colname, tablename)
        COLNAME = colname.upper()
        fmtdict['COLNAME'] = COLNAME
        fmtdict['col'] = col
        for parent, child in ut.itertwo(depends_list):
            fmtdict['parent'] = parent
            fmtdict['PARENT'] = parent.upper()
            fmtdict['child'] = child
            fmtdict['TABLE'] = tbl2_TABLE[child]  # tblname1_TABLE[child]
            #append_func(get_dependency_template.format(**fmtdict))

    func_list.append('    # --- %s NATIVE PROPERTIES --- ' % (tablename.upper()))

    for colname in other_colnames:
        col = colname2_col(colname, tablename)
        COLNAME = colname.upper()
        fmtdict['COLNAME'] = COLNAME
        fmtdict['col'] = col
        # tblname is the last child
        fmtdict['tbl'] = child
        fmtdict['TABLE'] = tbl2_TABLE[child]  # [child]
        append_func(get_column_template.format(**fmtdict))

    fmtdict['child_colnames'] = all_colnames

    append_func(add_dependent_child_stub_template.format(**fmtdict))

    append_func(get_child_config_rowid_template.format(**fmtdict))
    return func_list


def main(ibs):
    tblname_list = [constants.CHIP_TABLE, constants.FEATURE_TABLE, constants.RESIDUAL_TABLE]
    sqldb = ibs.dbcache
    db = sqldb  # NOQA
    #child = 'featweight'
    for tablename in tblname_list:
        #print('__')
        all_colnames = sqldb.get_column_names(tablename)
        #superkey_colnames = sqldb.get_table_superkey_colnames(tablename)
        #print(superkey_colnames)
        #primarykey_colnames = sqldb.get_table_primarykey_colnames(tablename)
        other_colnames = sqldb.get_table_otherkey_colnames(tablename)
        #print(other_colnames)

        if tablename in ibs.dbcache.get_table_names():
            sqldb_ = 'dbcache'
        else:
            sqldb_ = 'db'
        func_list = build_dependent_controller_funcs(tablename, other_colnames, all_colnames, sqldb_)
        print('\n\n'.join(func_list))

#if __name__ == '__main__':
if 'ibs' not in vars():
    import ibeis
    ibs = ibeis.opendb('ibs')
#ibs = None
main(ibs)

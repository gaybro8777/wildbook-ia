# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut
from ibeis.templates import notebook_cells


def generate_notebook_report(ibs):
    r"""

    CommandLine:
        python -m ibeis --tf generate_notebook_report --db lynx --run
        python -m ibeis --tf generate_notebook_report --db lynx --ipynb
        python -m ibeis --tf generate_notebook_report --db PZ_Master1 --ipynb
        python -m ibeis --tf generate_notebook_report --db PZ_Master1 --hacktestscore --ipynb
        python -m ibeis --tf generate_notebook_report --db PZ_Master1 --hacktestscore --run
        jupyter-notebook Experiments-lynx.ipynb
        killall python

    Example:
        >>> # SCRIPT
        >>> from ibeis.templates.generate_notebook import *  # NOQA
        >>> import ibeis
        >>> ibs = ibeis.opendb(defaultdb='testdb1')
        >>> result = generate_notebook_report(ibs)
        >>> print(result)
    """
    dbname = ibs.get_dbname()
    fname = 'Experiments-' + dbname
    nb_fpath = fname + '.ipynb'
    notebook_str = make_ibeis_notebook(ibs)
    ut.writeto(nb_fpath, notebook_str)
    if ut.get_argflag('--run'):
        run_nb = run_ipython_notebook(notebook_str)
        output_fpath = export_notebook(run_nb, fname)
        ut.startfile(output_fpath)
    elif ut.get_argflag('--ipynb'):
        ut.startfile(nb_fpath)
    else:
        print('notebook_str =\n%s' % (notebook_str,))


def get_default_cell_template_list():
    cell_template_list = [
        notebook_cells.initialize,
        notebook_cells.annot_config_info,
        notebook_cells.pipe_config_info,
        #notebook_cells.timestamp_distribution,
        #notebook_cells.detection_summary,
        notebook_cells.per_annotation_accuracy,
        notebook_cells.per_name_accuracy,
        notebook_cells.timedelta_distribution,
        #notebook_cells.dbsize_expt,
        #notebook_cells.all_scores,
        #notebook_cells.success_scores,
        notebook_cells.success_cases,
        notebook_cells.failure_type1_cases,
        notebook_cells.failure_type2_cases,
        #notebook_cells.investigate_specific_case,
        #notebook_cells.view_intereseting_tags,
    ]
    return cell_template_list


def export_notebook(run_nb, fname):
    import IPython.nbconvert.exporters
    import codecs
    #exporter = IPython.nbconvert.exporters.PDFExporter()
    exporter = IPython.nbconvert.exporters.HTMLExporter()
    output, resources = exporter.from_notebook_node(run_nb)
    ext = resources['output_extension']
    output_fpath = fname + ext
    #codecs.open(output_fname, 'w', encoding='utf-8').write(output)
    codecs.open(output_fpath, 'w').write(output)
    return output_fpath
    #IPython.nbconvert.exporters.export_python(runner.nb)


def run_ipython_notebook(notebook_str):
    """
    References:
        https://github.com/paulgb/runipy
        >>> from ibeis.templates.generate_notebook import *  # NOQA
    """
    from runipy.notebook_runner import NotebookRunner
    import nbformat
    import logging
    log_format = '%(asctime)s %(levelname)s: %(message)s'
    log_datefmt = '%m/%d/%Y %I:%M:%S %p'
    logging.basicConfig(
        level=logging.INFO, format=log_format, datefmt=log_datefmt
    )
    #fpath = 'tmp.ipynb'
    #notebook_str = ut.readfrom(fpath)
    #nb3 = IPython.nbformat.reads(notebook_str, 3)
    #cell = nb4.cells[1]
    #self = runner
    #runner = NotebookRunner(nb3, mpl_inline=True)
    print('Executing IPython notebook')
    nb4 = nbformat.reads(notebook_str, 4)
    runner = NotebookRunner(nb4)
    runner.run_notebook(skip_exceptions=False)
    run_nb = runner.nb
    return run_nb


def make_ibeis_notebook(ibs):
    r"""
    Args:
        ibs (IBEISController):  ibeis controller object

    CommandLine:
        python -m ibeis.templates.generate_notebook --exec-make_ibeis_notebook
        python -m ibeis --tf make_ibeis_notebook --db lynx
        jupyter-notebook tmp.ipynb

        runipy tmp.ipynb --html report.html
        runipy --pylab tmp.ipynb tmp2.ipynb

        sudo pip install runipy

        python -c "import runipy; print(runipy.__version__)"

    Example:
        >>> # SCRIPYT
        >>> from ibeis.templates.generate_notebook import *  # NOQA
        >>> import ibeis
        >>> ibs = ibeis.opendb(defaultdb='testdb1')
        >>> notebook_str = make_ibeis_notebook(ibs)
        >>> print(notebook_str)
    """
    cell_template_list = get_default_cell_template_list()
    def make_autogen_str():
        import sys
        autogenkw = dict(
            stamp=ut.timestamp('printable'),
            regen_cmd=' '.join(sys.argv)
        )
        return ut.codeblock(
            '''
            # Autogenerated on {stamp}
            # Regen Command:
            #    {regen_cmd}
            #
            '''
        ).format(**autogenkw)
    autogen_str = make_autogen_str()
    dbname = ibs.get_dbname()
    if ut.get_argflag('--hacktestscore'):
        annotconfig_list_body = ut.codeblock(
            '''
            'timectrl',
            '''
        )
    else:
        annotconfig_list_body = ut.codeblock(
            '''
            'default:is_known=True',
            #'default:qsame_encounter=True,been_adjusted=True,excluderef=True'
            #'default:qsame_encounter=True,been_adjusted=True,excluderef=True,qsize=10,dsize=20',
            #'timectrl:',
            #'timectrl:qsize=10,dsize=20',
            #'timectrl:been_adjusted=True,dpername=3',
            #'unctrl:been_adjusted=True',
            '''
        )
    if ut.get_argflag('--hacktestscore'):
        pipeline_list_body = ut.codeblock(
            '''
            'default:lnbnn_on=True,bar_l2_on=False,normonly_on=False,fg_on=True',
            'default:lnbnn_on=False,bar_l2_on=True,normonly_on=False,fg_on=True',
            'default:lnbnn_on=False,bar_l2_on=False,normonly_on=True,fg_on=True',
            'default:lnbnn_on=True,bar_l2_on=False,normonly_on=False,fg_on=False',
            'default:lnbnn_on=False,bar_l2_on=True,normonly_on=False,fg_on=False',
            'default:lnbnn_on=False,bar_l2_on=False,normonly_on=True,fg_on=False',
            '''
        )
    elif True:
        pipeline_list_body = ut.codeblock(
            '''
            'default',
            #'default:K=1',
            #'default:K=1,adapteq=True',
            #'default:K=1,AI=False',
            #'default:K=1,AI=False,QRH=True',
            #'default:K=1,RI=True,AI=False',
            '''
        )
    locals_ = locals()
    from functools import partial
    _format = partial(format_cells, locals_=locals_)
    cell_list = ut.flatten(map(_format, cell_template_list))
    notebook_str = make_notebook(cell_list)
    return notebook_str


def format_cells(block, locals_={}):
    if isinstance(block, tuple):
        header, code = block
    else:
        header = None
        code = block
    code = code.format(**locals_)
    if header is not None:
        return [markdown_cell(header), code_cell(code)]
    else:
        return [code_cell(code)]


def code_cell(sourcecode):
    r"""
    Args:
        sourcecode (str):

    Returns:
        str: json formatted ipython notebook code cell

    CommandLine:
        python -m ibeis.templates.generate_notebook --exec-code_cell

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.templates.generate_notebook import *  # NOQA
        >>> sourcecode = notebook_cells.timestamp_distribution[1]
        >>> sourcecode = notebook_cells.initialize[1]
        >>> result = code_cell(sourcecode)
        >>> print(result)
    """
    from ibeis.templates.template_generator import remove_sentinals
    sourcecode = remove_sentinals(sourcecode)
    cell_header = ut.codeblock(
        """
        {
         "cell_type": "code",
         "execution_count": null,
         "metadata": {
          "collapsed": true
         },
         "outputs": [],
         "source":
        """)
    cell_footer = ut.codeblock(
        """
        }
        """)
    if sourcecode is None:
        source_line_repr = ' []\n'
    else:
        lines = sourcecode.split('\n')
        line_list = [line + '\n' if count < len(lines) else line
                     for count, line in enumerate(lines, start=1)]
        #repr_line_list = [repr_single(line) for line in line_list]
        repr_line_list = [repr_single(line) for line in line_list]
        source_line_repr = ut.indent(',\n'.join(repr_line_list), ' ' * 2)
        source_line_repr = ' [\n' + source_line_repr + '\n ]\n'
    return (cell_header + source_line_repr + cell_footer)


def markdown_cell(markdown):
    r"""
    Args:
        markdown (str):

    Returns:
        str: json formatted ipython notebook markdown cell

    CommandLine:
        python -m ibeis.templates.generate_notebook --exec-markdown_cell

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.templates.generate_notebook import *  # NOQA
        >>> markdown = '# Title'
        >>> result = markdown_cell(markdown)
        >>> print(result)
    """
    markdown_header = ut.codeblock(
        """
          {
           "cell_type": "markdown",
           "metadata": {},
           "source": [
        """
    )
    markdown_footer = ut.codeblock(
        """
           ]
          }
        """
    )
    return (markdown_header + '\n' +
            ut.indent(repr_single(markdown), ' ' * 2) +
            '\n' + markdown_footer)


def make_notebook(cell_list):
    header = ut.codeblock(
        """
        {
         "cells": [
        """
    )

    footer = ut.codeblock(
        """
         ],
         "metadata": {
          "kernelspec": {
           "display_name": "Python 2",
           "language": "python",
           "name": "python2"
          },
          "language_info": {
           "codemirror_mode": {
            "name": "ipython",
            "version": 2
           },
           "file_extension": ".py",
           "mimetype": "text/x-python",
           "name": "python",
           "nbconvert_exporter": "python",
           "pygments_lexer": "ipython2",
           "version": "2.7.6"
          }
         },
         "nbformat": 4,
         "nbformat_minor": 0
        }
        """)

    cell_body = ut.indent(',\n'.join(cell_list), '  ')
    notebook_str = header + '\n' + cell_body +  '\n' +  footer
    return notebook_str


def repr_single(s):
    if True:
        str_repr = ut.reprfunc(s)
        import re
        if str_repr.startswith('\''):
            inside = str_repr[1:-1]
            str_repr = '"' + re.sub('"', '\\"', inside) + '"'
        return str_repr
    else:
        return '"' + ut.reprfunc('\'' + s)[2:]


if __name__ == '__main__':
    """
    CommandLine:
        python -m ibeis.templates.generate_notebook
        python -m ibeis.templates.generate_notebook --allexamples
        python -m ibeis.templates.generate_notebook --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()

from __future__ import absolute_import, division, print_function
from six.moves import range
#import matplotlib.image as mpimg
from plottool import viz_image2
from plottool import interact_annotations
from plottool import draw_func2 as df2
from plottool import plot_helpers as ph
from plottool import interact_helpers as ih
from plottool import abstract_interaction

from matplotlib.widgets import Button  # NOQA
import matplotlib.pyplot as plt  # NOQA
import matplotlib as mpl  # NOQA
import six
import vtool as vt
#import utool
import utool as ut
ut.noinject(__name__, '[pt.interact_multiimage]')


BASE_CLASS = abstract_interaction.AbstractInteraction
#BASE_CLASS = object


class MultiImageInteraction(BASE_CLASS):
    """

    CommandLine:
        python -m plottool.interact_multi_image --exec-MultiImageInteraction --show

    Example:
        >>> # ENABLE_DOCTEST
        >>> from plottool.interact_multi_image import *  # NOQA
        >>> import utool as ut
        >>> TEST_IMAGES_URL = 'https://dl.dropboxusercontent.com/s/of2s82ed4xf86m6/testdata.zip'
        >>> test_image_dir = ut.grab_zipped_url(TEST_IMAGES_URL, appname='utool')
        >>> # test image paths
        >>> imgpaths       = ut.list_images(test_image_dir, fullpath=True, recursive=False)
        >>> bboxes_list = [[]] * len(imgpaths)
        >>> #bboxes_list[0] = [(-200, -100, 400, 400)]
        >>> bboxes_list[0] = [(20, 10, 400, 400)]
        >>> iteract_obj = MultiImageInteraction(imgpaths, nPerPage=4,
        >>>                                     bboxes_list=bboxes_list)
        >>> ut.show_if_requested()
    """

    def __init__(self, gpath_list, nPerPage=4, bboxes_list=None,
                 thetas_list=None, verts_list=None, gid_list=None, nImgs=None,
                 fnum=None,
                 context_option_funcs=None):
        print('Creating multi-image interaction')

    #def __init__(self, img_list, nImgs=None, gid_list=None, aids_list=None,
    #bboxes_list=None, nPerPage=10,fnum=None):
        if BASE_CLASS is not object:
            super(MultiImageInteraction, self).__init__(fnum=fnum)
        print('[pt] maX ', nPerPage)
        self.context_option_funcs = context_option_funcs
        if nImgs is None:
            nImgs = len(gpath_list)
        if BASE_CLASS is object:
            if fnum is None:
                self.fnum = df2.next_fnum()
        if bboxes_list is None:
            bboxes_list = [[]] * nImgs
        if thetas_list is None:
            thetas_list = [[0] * len(bboxes) for bboxes in bboxes_list]
        # How many images we are showing and per page
        self.thetas_list = thetas_list
        self.bboxes_list = bboxes_list
        if gid_list is None:
            self.gid_list = None
        else:
            self.gid_list = gid_list

        self.nImgs = nImgs
        self.nPerPage = min(nPerPage, nImgs)
        self.current_index = 0
        self.page_number = -1
        # Initialize iterator over the image paths
        self.gpath_list = gpath_list
        # Display the first page
        self.first_load = True
        self.scope = []
        self.current_pagenum = 0
        self.nPages = vt.iceil(self.nImgs / nPerPage)
        self.show_page()

    def make_hud(self):
        """ Creates heads up display """
        # Button positioning
        hl_slot, hr_slot = df2.make_bbox_positioners(y=.02, w=.08, h=.04,
                                                     xpad=.05, startx=0,
                                                     stopx=1)
        prev_rect = hl_slot(0)
        next_rect = hr_slot(0)

        # Create buttons
        if self.current_pagenum != 0:
            self.append_button('prev', callback=self.prev_page, rect=prev_rect)
        if self.current_pagenum != self.nPages - 1:
            self.append_button('next', callback=self.next_page, rect=next_rect)

    def next_page(self, event):
        print('next')
        self.show_page(self.current_pagenum + 1)
        pass

    def prev_page(self, event):
        self.show_page(self.current_pagenum - 1)
        pass

    def prepare_page(self, pagenum):
        """ Gets indexes for the pagenum ready to be displayed """
        # Set the start index
        self.start_index = pagenum * self.nPerPage
        # Clip based on nImgs
        self.nDisplay = min(self.nImgs - self.start_index, self.nPerPage)
        nRows, nCols = ph.get_square_row_cols(self.nDisplay)
        # Create a grid to hold nPerPage
        self.pnum_ = df2.get_pnum_func(nRows, nCols)
        # Adjust stop index
        self.stop_index = self.start_index + self.nDisplay
        # Clear current figure
        self.clean_scope()
        self.fig = df2.figure(fnum=self.fnum, pnum=self.pnum_(0),
                              doclf=True, docla=True)
        ih.disconnect_callback(self.fig, 'button_press_event')
        ih.connect_callback(self.fig, 'button_press_event',
                            self.on_click)

    def show_page(self, pagenum=None):
        """ Displays a page of matches """
        if pagenum is None:
            pagenum = self.current_pagenum
        #print('[iqr2] show page: %r' % pagenum)
        self.current_pagenum = pagenum
        self.prepare_page(pagenum)
        # Begin showing matches
        index = self.start_index
        start_index = self.start_index
        stop_index = self.stop_index
        for px, index in enumerate(range(start_index, stop_index)):
            self.plot_image(index)
        self.make_hud()
        self.draw()

    def plot_image(self, index):
        px = index - self.start_index
        gpath      = self.gpath_list[index]

        _vizkw = {
            'fnum': self.fnum,
            'pnum': self.pnum_(px),
        }

        if ut.is_funclike(gpath):
            # override of plot image function
            gpath(**_vizkw)
            import plottool as pt
            ax = pt.gca()
        else:
            if isinstance(gpath, six.string_types):
                img = vt.imread(gpath)
            else:
                img = gpath

            bbox_list  = self.bboxes_list[index]
            #print('bbox_list %r in display for px: %r ' % (bbox_list, px))
            theta_list = self.thetas_list[index]

            label_list = [ix + 1 for ix in range(len(bbox_list))]
            #Add true values for every bbox to display
            sel_list = [True for ix in range(len(bbox_list))]
            _vizkw.update({
                #title should always be the image number
                'title': str(index),
                'bbox_list'  : bbox_list,
                'theta_list' : theta_list,
                'sel_list'   : sel_list,
                'label_list' : label_list,
            })
            #print(utool.dict_str(_vizkw))
            #print('vizkw = ' + utool.dict_str(_vizkw))
            _, ax = viz_image2.show_image(img, **_vizkw)
            #print(index)
            ph.set_plotdat(ax, 'bbox_list', bbox_list)
            ph.set_plotdat(ax, 'gpath', gpath)
        ph.set_plotdat(ax, 'px', str(px))
        ph.set_plotdat(ax, 'index', index)

    def update_images(self, img_ind, updated_bbox_list, updated_theta_list,
                      changed_annottups, new_annottups):
        """Insert code for viz_image2 redrawing here"""
        #print('update called')
        index = int(img_ind)
        #print('index: %r' % index)
        #print('Images bbox before: %r' % (self.bboxes_list[index],))
        self.bboxes_list[index] = updated_bbox_list
        self.thetas_list[index] = updated_theta_list
        #print('Images bbox after: %r' % (self.bboxes_list[index],))
        self.plot_image(index)
        self.draw()

    def on_click(self, event):
        #don't do other stuff if we clicked a button
        #point = (event.x, event.y)
        #if (self.next_ax.contains_point(point) or
        #    self.prev_ax.contains_point(point)):
            #print('in button click')
            #return
        if not ih.clicked_inside_axis(event):
            return
        ax = event.inaxes
        index = ph.get_plotdat(ax, 'index')
        print('index = %r' % (index,))
        if index is not None:
            if self.context_option_funcs is not None:
                if event.button == 3:
                    options = self.context_option_funcs[index]()
                    self.show_popup_menu(options, event)
            else:
                #bbox_list  = ph.get_plotdat(ax, 'bbox_list')
                gpath = self.gpath_list[index]
                bbox_list = self.bboxes_list[index]
                print('Bbox of figure: %r' % (bbox_list,))
                theta_list = self.thetas_list[index]
                print('theta_list = %r' % (theta_list,))
                #img = mpimg.imread(gpath)
                if isinstance(gpath, six.string_types):
                    img = vt.imread(gpath)
                else:
                    img = gpath
                fnum = df2.next_fnum()
                mc = interact_annotations.ANNOTATIONInteraction(
                    img, index, self.update_images, bbox_list=bbox_list,
                    theta_list=theta_list, fnum=fnum)
                self.mc = mc
                # """wait for accept
                # have a flag to tell if a bbox has been changed, on the bbox
                # list that is brought it" on accept: viz_image2.show_image
                # callback
                # """
                df2.update()
            print('Clicked: ax: num=%r' % index)

    def on_key_press(self, event):
        if event.key == 'n':
            self.display_next_page()
        if event.key == 'p':
            self.display_prev_page()

    #def clean_scope(self):
    #    """ Removes any widgets saved in the interaction scope """
    #    #for (but, ax) in self.scope:
    #    #    but.disconnect_events()
    #    #    ax.set_visible(False)
    #    #    assert len(ax.callbacks.callbacks) == 0
    #    self.scope = []

    #def draw(self):
    #    self.fig.canvas.draw()

    #def append_button(self, text, divider=None, rect=None, callback=None,
    #                  **kwargs):
    #    """ Adds a button to the current page """
    #    if divider is not None:
    #        new_ax = divider.append_axes('bottom', size='9%', pad=.05)
    #    if rect is not None:
    #        new_ax = df2.plt.axes(rect)
    #    new_but = mpl.widgets.Button(new_ax, text)
    #    if callback is not None:
    #        new_but.on_clicked(callback)
    #    ph.set_plotdat(new_ax, 'viztype', 'button')
    #    ph.set_plotdat(new_ax, 'text', text)
    #    for key, val in six.iteritems(kwargs):
    #        ph.set_plotdat(new_ax, key, val)
    #    # Keep buttons from losing scrop
    #    self.scope.append((new_but, new_ax))

    #def display_buttons(self):
    #    # Create the button for scrolling forwards
    #    self.next_ax = plt.axes([0.75, 0.025, 0.15, 0.075])
    #    self.next_but = Button(self.next_ax, 'next')
    #    self.next_but.on_clicked(self.display_next_page)

    #    # Create the button for scrolling backwards
    #    self.prev_ax = plt.axes([0.1, .025, 0.15, 0.075])
    #    self.prev_but = Button(self.prev_ax, 'prev')
    #    self.prev_but.on_clicked(self.display_prev_page)
    #    # Connect the callback whenever the figure is clicked


if __name__ == '__main__':
    """
    CommandLine:
        python -m plottool.interact_multi_image
        python -m plottool.interact_multi_image --allexamples
        python -m plottool.interact_multi_image --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()

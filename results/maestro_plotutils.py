import argparse
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, FixedLocator, FixedFormatter
import math
from tabulate import tabulate
import itertools
import os
import importlib
from IPython.display import Image, display, HTML
import glob
import re
import seaborn as sns

# =================================================================
# Returns true if running inside a jupyter notebook,
# false when running as a simple python script
# useful for handling command line options or
# setting up notebook defaults
# =================================================================
def is_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter

# =================================================================
# customize/configure the size of jupyter output
# inside a notebook (window width)
# =================================================================
if is_notebook():
    # this makes the notebook wider on a larger screen using %x of the display
    display(HTML("<style>.container { width:100% !important; }</style>"))

# =================================================================
# Tell pandas to display more columns without wrapping in dataframe output
# =================================================================
pd.set_option('display.max_rows',    30)
pd.set_option('display.max_columns', 30)
pd.set_option('display.width',       1000)

# =================================================================
# For debugging : print any object
# uses the default print function for any object
# - pandas dataframes will be limited in output size
# =================================================================
def title_print(string, thing):
    print('\n' + '-'*20, '\n' + string, '\n' + '-'*20)
    print(thing)
    print('\n' + '-'*20)

# =================================================================
# For debugging : print all data in a dataframe
# warning: this can produce huge output since pandas will
# show all/unlimited rows/columns
# =================================================================
def title_print_all(string, thing):
    print('\n' + '-'*20, '\n' + string, '\n' + '-'*20)
    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None,
                           'display.width', 1000):
        print(thing)
    print('\n' + '-'*20)

# =================================================================
# For debugging : print a dataframe (summary including column types)
# =================================================================
def title_print_dataframe(string, df):
    print('\n' + '-'*20, '\n' + string, '\n' + '-'*20)
    print(df.dtypes)
    print(df)
    print('\n' + '-'*20)

# =================================================================
# For debugging : print dataframe in table form
# =================================================================
def tab_print(string, dframe, show_index=True):
    print('\n' + '-'*20, '\n' + string, '\n' + '-'*20)
    print(tabulate(dframe, headers='keys', tablefmt='psql', floatfmt=".1f", showindex=show_index))
    print('\n' + '-'*20)

# =================================================================
# Print a dataframe with column headers aligned a bit better when they are wrong
# nb. can mess up when index has spaces, such as "date time"
# =================================================================
blanks = r'^ *([a-zA-Z_0-9-]*) .*$'
blanks_comp = re.compile(blanks)

def pretty_to_string(df):

    def find_index_in_line(line):
        index = 0
        spaces = False
        for ch in line:
            if ch == ' ':
                spaces = True
            elif spaces:
                break
            index += 1
        return index

    lines = df.to_string().split('\n')
    header = lines[0]
    m = blanks_comp.match(header)
    indices = []
    if m:
        st_index = m.start(1)
        indices.append(st_index)

    non_header_lines = lines[1:len(lines)]

    for line in non_header_lines:
        index = find_index_in_line(line)
        indices.append(index)

    mn = np.min(indices)
    newlines = []
    for l in lines:
        newlines.append(l[mn:len(l)])

    return '\n'.join(newlines)

# =================================================================
# Trim spaces from all strings in dataframe
# =================================================================
def trim_all_columns(df):
    """
    Trim whitespace from ends of each value across all series in dataframe
    """
    trim_strings = lambda x: x.strip() if isinstance(x, str) else x
    return df.applymap(trim_strings)

# -------------------------------------------------
# Convenience function to remove unwanted columns
# -------------------------------------------------
def drop_columns_except(df, cols, in_place=True):
    df = df.drop(df.columns.difference(cols), axis=1, inplace=in_place)
    return df

# -------------------------------------------------
# Convenience function to remove unwanted columns
# -------------------------------------------------
def drop_columns(df, cols, in_place=True):
    df = df.drop(cols, axis=1, inplace=in_place)
    return df

# =================================================================
# Takes axes from subplot and makes a grid even when r==1 or c==1
# access grid using axes[r][c]
# =================================================================
def axes_to_row_col_grid(rows, cols, ax):
    axes = ax
    if rows==1:
        axes = [axes]
    if cols==1:
        axes = [[a] for a in axes]
    return axes

# =================================================================
# Global dataset management
# =================================================================
global_dataframe = pd.DataFrame()
global_datadict = {}

def add_to_global_data(data, dirname):
    global global_dataframe
    global global_datadict
    if dirname in global_datadict:
        print('Data previously loaded {} lines'.format(len(global_dataframe.index)))
    else:
        global_dataframe = pd.concat([global_dataframe, data], ignore_index=True, sort=False)
        global_datadict[dirname] = 1
        print('Total data loaded {} lines'.format(len(global_dataframe.index)))
    return global_dataframe

# =================================================================
# Miscellaneous list flattening including numpy arrays (graphs lists)
# =================================================================
def flatten(x):
    if isinstance(x, list) or isinstance(x, np.ndarray):
        return [a for i in x for a in flatten(i)]
    else:
        return [x]

# Read a CSV file and convert the known numeric columns to float types
def read_pandas_csv(filename):
    print('Reading', filename)
    data = pd.read_csv(filename, index_col=0)
    for col in ['futures', 'time', 'ftime', 'numa', 'threads']:
        data[col] = data[col].astype(float)
    return data

def load_csv_files_in_dir(dirname):
    data = pd.DataFrame()
    filenames = glob.glob(os.path.join(dirname, '*-*.csv'))
    for filename in filenames :
        data = pd.concat([data, read_pandas_csv(filename)], sort=False)
    add_to_all_data(data, dirname)

# =================================================================
# Holder for axis info for plot routine
# =================================================================
class axis(object):
    def __init__(self,
                 label='No label',
                 limits=None,
                 scale='linear', base=10,
                 format=lambda v,pos: str(int(v)),
                 majloc=None, minloc=None,
                 fontsize=12):

        self.label    = label
        self.limits   = limits
        self.scale    = scale
        self.base     = base
        self.format   = format
        self.majloc   = majloc
        self.minloc   = minloc
        self.fontsize = fontsize

# =================================================================
# Holder for info for row/col heeaders plot routine
# =================================================================
class rowcol(object):
    def __init__(self,
                 label='No Column',
                 format=lambda v: str(v),
                 fontsize=12,
                 rearrange=True):

        self.label     = label
        self.format    = format
        self.fontsize  = fontsize
        self.rearrange = rearrange

# =================================================================
# Holder for legend params
# =================================================================
class legend(object):
    def __init__(self,
                 enabled=True,
                 loc='best',
                 ncol=1,
                 format=lambda v: str(v),
                 fontsize=12,
                 fontname='Arial'
                ):

        self.enabled  = enabled
        self.loc      = loc
        self.ncol     = ncol
        self.fontsize = fontsize
        self.fontname = fontname
        self.format   = format

# =================================================================
# Holder for series params
# =================================================================
class series(object):
    def __init__(self,
                 colors     = ('blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan'),
                 linestyle  = ('-','--','-.',':'),
                 markers    = ('+', '.', 'o', '*', '^', 's', 'v', '<', '>', '8', 's', 'p', 'h', 'H', 'D', 'd', ','),
                 linewidth  = 2,
                 markersize = 6
                ):

        self.colors     = colors
        self.linestyle  = linestyle
        self.linewidth  = linewidth
        self.markers    = markers
        self.markersize = markersize

# =================================================================
# Plot combinations of series
# =================================================================
def plot_graph_series(data, Rows, Cols, select, plotvars, xparams, yparams,
                      cparams=None, rparams=None, lparams=None, sparams=None, size=(8,4,150)):

    # select only the data wanted
    for series in select:
        #print('selecting', series, select[series])
        if isinstance(select[series], list):
            #print('We got a list', select[series])
            data = data[data[series].isin(select[series])]
        else:
            data = data[data[series] == select[series]]

    # decide how many rows, columns will be needed
    num_rows = 1
    num_cols = 1
    if len(Cols)>0:
        #print('columns', Cols)
        num_cols = 0
        for col in Cols:
            unique_col_entries = data[col].unique().tolist()
            unique_col_entries.sort()
            num_cols = num_cols + len(unique_col_entries)
    if len(Rows)>0:
        #print('rows', Rows)
        num_rows = 0
        for row in Rows:
            unique_row_entries = data[row].unique().tolist()
            unique_row_entries.sort()
            num_rows = num_rows + len(unique_row_entries)

    # don't like having a single row with many graphs crammed into it, so use multiple rows
    single_row_modified = False
    mod_rows = num_rows
    mod_cols = num_cols
    allow_rearranging = rparams is not None and rparams.rearrange==True
    if allow_rearranging and len(Rows)==0 and num_cols>1:
        mod_rows = math.floor(math.sqrt(num_cols)+1)
        mod_cols = math.ceil(1.0*num_cols/mod_rows)
        single_row_modified = True
        print('Overriding graph layout cols={}, rows={}'.format(mod_cols,mod_rows))

    #print('Using Rows {}, Cols {}'.format(num_rows, num_cols))

    # break the wanted data into groups of series
    grouplist = []
    xvar = ''
    yvar = ''
    for entry in plotvars:
        if entry=='y':
            yvar = plotvars[entry]
            pass
        elif entry=='x':
            xvar = plotvars[entry]
            pass
        else:
            grouplist = plotvars[entry] + grouplist

    #print('x', xvar, 'y', yvar, 'Grouplist', grouplist)
    width  = np.clip(size[0]*mod_cols, size[0], 20)
    height = size[1]*mod_rows
    dpi    = size[2]
    fig, axes = plt.subplots(nrows = mod_rows, ncols = mod_cols, figsize=(width,height), dpi=dpi, facecolor='w', edgecolor='k')
    graph_rows_cols = axes_to_row_col_grid(mod_rows, mod_cols, axes)
    #print(num_rows, num_cols, graph_rows_cols)

    if sparams is not None:
        colors     = sparams.colors
        markersize = sparams.markersize
        markers    = sparams.markers
        linestyle  = sparams.linestyle
        linewidth  = sparams.linewidth
    else:
        colors     = ('blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan')
        markersize = 6
        markers    = ('+', '.', 'o', '*', '^', 's', 'v', '<', '>', '8', 's', 'p', 'h', 'H', 'D', 'd', ',')
        linestyle  = ('-')
        linewidth  = 2

    filled_markers = ('o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd')
    majorLocator   = MultipleLocator(5)
    majorFormatter = FormatStrFormatter('%d')
    minorLocator   = MultipleLocator(1)

    grouplen = 1
    
    def plot_series_recursive(data, x, y, groups, prefix, ax1, fmt):
        print('Groups', groups, 'x', x, 'y',y)
        if len(groups)>0:
            head, tail = groups[0], groups[1:]
            #print('Grouping by', head)
        else:
            mean = data.groupby(['IO', x]).mean().reset_index()
            mean = mean.sort_values('IO', axis=0, ascending=False, inplace=False, kind='quicksort', na_position='last', ignore_index=False, key=None)

            #title_print('Data', mean)
            sns.barplot(x=x, y=y, data=mean, hue='IO', ax=ax1)
            # ax1.xaxis.set_major_locator(FixedLocator(np.arange(0, 20, 1)))
            # ax1.xaxis.set_major_formatter(FixedFormatter(x[::1]))
            #ax1.tick_params(axis="x", rotation=90)

    # ------------------------------------------------
    for row in range(num_rows):
        rsubset = data
        if num_rows>1:
            #print('Selecting row using ', Rows[0], unique_row_entries[row])
            rsubset = data[data[Rows[0]]==unique_row_entries[row]]
        for col in range(num_cols):
            csubset = rsubset
            if num_cols>1:
                #print('Selecting column using ', Cols[0], unique_col_entries[col])
                csubset = rsubset[rsubset[Cols[0]]==unique_col_entries[col]]
            if not single_row_modified:
                ax1 = graph_rows_cols[row][col]
            else:
                mcol = col %  mod_cols
                mrow = col // mod_cols
                ax1 = graph_rows_cols[mrow][mcol]

            # restart markers and colours from beginning of list for each new graph
            localmarkers   = itertools.cycle(markers)
            locallinestyle = itertools.cycle(linestyle)
            localcolor     = itertools.cycle(colors)

            lfmt = None
            if lparams is not None:# and lparams.enabled:
                lfmt = lparams.format
            plot_series_recursive(csubset, xvar, yvar, grouplist, '', ax1, lfmt)

            # ------------------------------------------------
            if xparams.limits is not None:
                ax1.set_xlim(xparams.limits[0], xparams.limits[1])
            if xparams.scale is not None:
                ax1.set_xscale(xparams.scale) # , basex=xparams.base)
            if xparams.label is not None:
                ax1.set_xlabel(xparams.label, fontsize=xparams.fontsize)
            # if xparams.format is not None:
            #     ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(xparams.format))
            if xparams.majloc is not None:
                ax1.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(xparams.majloc))
            if xparams.minloc is not None:
                ax1.xaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(xparams.minloc))
            if (xparams.majloc is not None) and (xparams.minloc is not None):
                ax1.xaxis.set_ticks_position('both')

            # ------------------------------------------------
            if yparams.limits is not None:
                ax1.set_ylim(yparams.limits[0], yparams.limits[1])
            if yparams.scale is not None:
                ax1.set_yscale(yparams.scale) #, basey=yparams.base)
            if yparams.label is not None:
                ax1.set_ylabel(yparams.label, fontsize=yparams.fontsize)
            if yparams.format is not None:
                ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(yparams.format))
            if yparams.majloc is not None:
                ax1.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(yparams.majloc))
            if yparams.minloc is not None:
                ax1.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(yparams.minloc))
            if (yparams.majloc is not None) and (yparams.minloc is not None):
                ax1.yaxis.set_ticks_position('both')

            if lparams is not None:
                if lparams.enabled:
                    lfmt = lparams.format
                    leg = ax1.legend(loc=lparams.loc, ncol=lparams.ncol)
                    plt.setp(leg.texts, family=lparams.fontname, fontsize=lparams.fontsize)
                else:
                    ax1.legend().remove()
            else:
                ax1.legend(loc='best', ncol=1)

    if single_row_modified:
        for txt, col in zip(unique_col_entries, range(len(unique_col_entries))):
            mcol = col %  mod_cols
            mrow = col // mod_cols
            ax = graph_rows_cols[mrow][mcol]
            if (cparams is not None) and (cparams.format is not None):
                txt = cparams.format(Cols[0], txt)
            ax.annotate(txt,
                        xy=(0.5, 1), xytext=(0, 10),
                        xycoords='axes fraction', textcoords='offset points',
                        size='large', ha='center', va='baseline')
    else:
        if len(Cols)>0:
            for txt, col in zip(unique_col_entries, range(len(unique_col_entries))):
                ax = graph_rows_cols[0][col]
                if (cparams is not None) and (cparams.format is not None):
                    txt = cparams.format(Cols[0], txt)
                ax.annotate(txt,
                            xy=(0.5, 1), xytext=(0, 10),
                            xycoords='axes fraction', textcoords='offset points',
                            size='large', ha='center', va='baseline')
        if len(Rows)>0:
            for txt, row in zip(unique_row_entries, range(len(unique_row_entries))):
                ax = graph_rows_cols[row][0]
                if (rparams is not None) and (rparams.format is not None):
                    txt = rparams.format(Rows[0], txt)
                ax.annotate(txt,
                    xy=(0, 0.5), xytext=(-ax.yaxis.labelpad - 32, 0),
                    xycoords=ax.yaxis.label, textcoords='offset points',
                    size='large', ha='right', va='center')
    plt.tight_layout()
    return fig , graph_rows_cols

#!/usr/bin/env python
''' find_high_cross_correlations.py

Help find more matches for training

Prerequisites:
    - You should have run `opensoundscape.py spect_gen -i <ini>`
    - You should have run `opensoundscape.py model_fit -i <ini>`
    - The <ini>'s must match!

Usage:
    find_high_cross_correlations.py <label> [-i <ini>] [-s <template_pool.csv>] [-c <chunk_size>] [-hv]

Positional Arguments:
    <label>             The label you would like to interrogate,
                            must be in the CSV defined as `train_file`

Options:
    -h --help                       Print this screen and exit
    -v --version                    Print the version of crc-squeue.py
    -i --ini <ini>                  Specify an override file [default: opensoundscape.ini]
    -s --save <template_pool.csv>   Generate a <template_pool.csv> for opensoundscape.py
'''

def generate_ff_stats(stats_df, species_found_df):
    items = return_cursor(list(stats_df.index.values), 'statistics', config)

    all_file_file_statistics = [None] * stats_df.shape[0]
    for idx, item in enumerate(items):
        _, file_file_stats = cursor_item_to_stats(item)
        all_file_file_statistics[idx] = [file_file_stats[found] for found in species_found_df.index.values]

    # Stack internal stats
    # -> convert to NP array
    # -> extract only template matching stat specifically [:, :, 0]
    npify = [None] * stats_df.shape[0]
    for o_idx, outer in enumerate(all_file_file_statistics):
        stack = np.vstack([all_file_file_statistics[o_idx][x] for x in range(len(all_file_file_statistics[o_idx]))])
        npify[o_idx] = copy(stack)
    all_file_file_statistics = np.array(npify)[:, :, 0]

    return all_file_file_statistics

def high_cc(l, species_found, config):
    if len(l) != 0:
        init_client(config)
        all_file_file_statistics = generate_ff_stats(l, species_found)
        close_client()

        try:
            results_str = ""
            for idx, row in zip(l.index.values, all_file_file_statistics):
                highest_cc = row.max()
                if highest_cc >= 0.75:
                    build_str = np.array_str(row).replace('\n', '')
                    results_str += f"{idx}: {build_str}\n"
        except ValueError:
            pass

        return results_str
    else:
        return ""

from docopt import docopt
import pandas as pd
import numpy as np
from copy import copy
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat

# Need some functions from our module
import sys
script_dir = sys.path[0]
sys.path.insert(0, f"{script_dir}/..")

from modules.utils import generate_config, return_cpu_count
from modules.db_utils import init_client
from modules.db_utils import close_client
from modules.db_utils import cursor_item_to_stats
from modules.db_utils import return_cursor

# From the docstring, generate the arguments dictionary
arguments = docopt(__doc__, version='find_high_cross_correlations.py version 0.0.1')

# Generate the config instance
config = generate_config('config/opensoundscape.ini', arguments['--ini'])

# Generate list of files which identify <label>
labels_df = pd.read_csv(f"{config['general']['data_dir']}/{config['general']['train_file']}",
    index_col="Filename")
labels_df = labels_df.fillna(0).astype(int)

# Downsample to particular species
species = arguments["<label>"]

# Identify files with and without bird
species_found = labels_df[species][labels_df[species] == 1]
species_not_found = labels_df[species][labels_df[species] == 0]

nprocs = return_cpu_count(config)

chunk_species_not_found = np.array_split(species_not_found, nprocs)
chunk_species_found = np.array_split(species_found, nprocs)

with ProcessPoolExecutor(nprocs) as executor:
    results = executor.map(high_cc, chunk_species_not_found, repeat(species_found), repeat(config))

for res in results:
    if res != "":
        print(res)

print("--> Identified <--")

with ProcessPoolExecutor(nprocs) as executor:
    results = executor.map(high_cc, chunk_species_found, repeat(species_found), repeat(config))

for res in results:
    if res != "":
        print(res)

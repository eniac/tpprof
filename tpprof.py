#!/usr/bin/python3

from lib.common import *
import lib.drawing
import lib.clustering
import lib.parsing
import lib.subsequencing
from lib.subsequence_objective import function as subsequence_objective

import argparse
import errno
from hyperopt import fmin, tpe, hp, Trials, STATUS_OK
if PARALLEL:
    from hyperopt.mongoexp import MongoTrials
import numpy as np
import pickle
import os
import sys


def argParser():
    parser = argparse.ArgumentParser(
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('datafile', type=str, help='The raw data file.')
    parser.add_argument('--resultprefix', type=str,
                        help='The prefix of result files. Default is ' \
                             'tmp/ + datafile between the last / and .')
    parser.add_argument('--seed', type=int, help='seed for hyperopt')
    parser.add_argument('--plot', dest='plot', action='store_true',
                        help='whether to open the plot at the end.')
    parser.add_argument('--noplot', dest='plot', action='store_false',
                        help='whether to open the plot at the end.')
    parser.set_defaults(plot=True)

    return parser.parse_args()

def main():
    args = argParser()

    datafile = args.datafile

    resultprefix = 'tmp/' + args.datafile.rpartition('/')[2].rpartition('.')[0]
    if args.resultprefix:
        resultprefix = args.resultprefix
    # mod: include clustering method in clustering filename. 
    cluster_file = resultprefix + '.cluster'
    subsequence_file = resultprefix + '.subsequence'
    graph_file = resultprefix + '.pdf'

    rstate = None
    seed_desc = "UNSET"
    if args.seed:
        rstate = np.random.RandomState(args.seed)
        seed_desc = str(args.seed)

    plot = args.plot

    print ('PARSER PARAMETERS: ')
    print ('--------------------')
    print ('\tinput file: %s' % datafile)
    print ('\tresult prefix: %s' % resultprefix)
    print ('\tgraph_file: %s' % graph_file)
    print ('\tsaved cluster results: %s' % os.path.isfile(cluster_file))
    print ('\tsaved subsequence results: %s' % os.path.isfile(subsequence_file))
    print ('\tseed: %s' % seed_desc)
    print ('\tparallel: %s' % ("Yes" if PARALLEL else "No"))
    print ('\tplot: %s' % ("Yes" if plot else "No"))
    print ("--------------------")


    # run clustering
    new_cluster = False

    if os.path.isfile(cluster_file):
        print("Loading previous clustering...")

        cluster_results = pickle.load(open(cluster_file, 'rb'))

        long_keys = ["original_pts", "clustered_pts"]
        printable_results = {k : v for k, v in cluster_results.items() \
                                       if k not in long_keys}
        print("Loaded clustering with parameters: " + str(printable_results))
    else:
        print("Generating clustering...")

        # get data
        input_data = lib.parsing.parseSwitchTrace(datafile)
        np_input_data = np.array(input_data)

        # clustering
        X = np_input_data
        Y = lib.clustering.runPipeline(bGmmConf, X)
        cluster_results = {}
        cluster_results['original_pts'] = input_data
        cluster_results['clustered_pts'] = pickle.dumps(Y)

        if not os.path.exists(os.path.dirname(cluster_file)):
            try:
                os.makedirs(os.path.dirname(cluster_file))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    print("problem here: ", cluster_file, " ",
                          os.path.dirname(cluster_file))
                    raise
        pickle.dump(cluster_results, open(cluster_file, 'wb'))
        new_cluster = True


    # run subsequencing
    if not new_cluster and os.path.isfile(subsequence_file):
        print("Loading previous subsequences...")

        subsequences = pickle.load(open(subsequence_file, 'rb'))

        long_keys = ["merged_freq", "coverage_sum"]
        printable_results = {k : v for k, v in subsequences.items() \
                                       if k not in long_keys}
        print("Loaded subsequences with parameters: " + str(printable_results))
    else:
        print("Generating subsequences...")

        space = {
            'min_frequency_thresh': hp.qlognormal('min_frequency_thresh',
                                                  4, 0.6, 1),
            'clustered_pts': cluster_results['clustered_pts']
        }

        if PARALLEL:
            trials = MongoTrials('mongo://localhost:45555/db/jobs',
                                 exp_key='tpprof1')
        else:
            trials = Trials()

        best = fmin(fn = subsequence_objective, space = space,
                    algo = tpe.suggest, max_evals = SUBSEQUENCE_EVALS,
                    trials = trials, rstate = rstate)
        best_trial = trials.trials[np.argmin([r['loss'] for r in trials.results])]
        subsequence_freq = pickle.loads(
                    trials.trial_attachments(best_trial)['subsequence_freq'])
        subsequence_coverage = pickle.loads(
                    trials.trial_attachments(best_trial)['subsequence_coverage'])

        merged_freq, coverage_sum = \
                lib.subsequencing.merge_stable(subsequence_freq,
                                               subsequence_coverage)
        best['merged_freq'] = merged_freq
        best['coverage_sum'] = coverage_sum

        subsequences = best
        pickle.dump(subsequences, open(subsequence_file, 'wb'))

    if plot:
        print("Drawing profile...")

        lib.drawing.plot(cluster_results['original_pts'],
                         pickle.loads(cluster_results['clustered_pts']),
                         subsequences['merged_freq'],
                         subsequences['coverage_sum'],
                         graph_file, plot)
    else:
        print('Drawing disabled')


if __name__ == '__main__':
    main()

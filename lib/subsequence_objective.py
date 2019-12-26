from lib.common import *
import lib.subsequencing

from hyperopt import STATUS_OK
import numpy as np
import os
import pickle
import sys

cacheDict = dict() # global so that we don't redo hyperparams
def function(params):
    params['clustered_pts'] = pickle.loads(params['clustered_pts'])
    print("Trial: " + str(params))

    clustered_pts = params['clustered_pts']
    min_frequency_thresh = int(params['min_frequency_thresh'])

    # TODO: old code remove soon
    if min_frequency_thresh < 2:
        params['min_frequency_thresh'] = 2
        min_frequency_thresh = int(params['min_frequency_thresh'])
        print('min_frequency_thresh less than 0.1%%.  Rounding up to %d' % \
              (min_frequency_thresh))

    # Remove the next line when passing max subsequence
    max_subsequence_len = len(clustered_pts) - 1

    global cacheDict
    if min_frequency_thresh in cacheDict:
        print("WARNING: Found repeat hyperparameter. Skipping.")
        return {'loss' : 0, 'input' : params, 'status': STATUS_OK}

    try:
        if not DEBUG:
            save_stdout = sys.stdout
            sys.stdout = DummyFile()
        subsequence_freq, subsequence_coverage, score = \
                lib.subsequencing.score_total_coverage(clustered_pts,
                                                       max_subsequence_len,
                                                       min_frequency_thresh)
        if not DEBUG:
            sys.stdout = save_stdout
    except np.linalg.LinAlgError:
        score = 0

    cacheDict[min_frequency_thresh] = -score
    subsequence_freq = pickle.dumps(subsequence_freq)
    subsequence_coverage = pickle.dumps(subsequence_coverage)
    return {'loss' : (-score), 'input' : params, 'status': STATUS_OK,
            'attachments': {'subsequence_freq': subsequence_freq,
                            'subsequence_coverage': subsequence_coverage}}
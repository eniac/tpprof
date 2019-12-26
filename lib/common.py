DEBUG = False
PARALLEL = False

import lib.clustering as cluster
from sklearn.mixture import GaussianMixture


# hyperparameter tuning for subsequencing
SUBSEQUENCE_EVALS = 10
GMM_TRIALS = 10

# configuration for GMM pipeline
bGmmConf = {
    "projectFcn" : cluster.pcaProject,
    "n_dim" : 2,
    "scoreClusterFcn" : GaussianMixture,
    "scoreFcn" : cluster.scoreBicKnee,
    "kRange" : range(2, 11),
    "nTrials" : GMM_TRIALS,
    "clusterFcn" : cluster.RegBayesianGmm,
    "n_init" : 10,
    "n_init_search" : 1
}

class DummyFile(object):
    def write(self, x): pass
    def flush(self): pass
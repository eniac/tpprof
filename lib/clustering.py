import argparse
import multiprocessing as mp
import numpy as np
from numpy import matlib as mlb
import os
import pandas as pd
import pickle
from sklearn.decomposition import PCA
from sklearn.mixture import BayesianGaussianMixture
import sys

import lib.parsing


def runPipeline(plConf, X):
    """ Run an ML pipeline defined by plConf, get Y vec """
    pl = build3StagePipe(plConf)
    pl.setX(X)
    pl.runStages()
    Y = pl.finalOut["Y"]
    return Y

def build3StagePipe(pipeConfigDict):
    # build pipe
    pl = MlPipeline(3)
    pl.stageType[0] = Project
    pl.stageType[1] = SelectK
    pl.stageType[2] = Cluster
    for k, v in pipeConfigDict.items():
        pl.stageArgs[0][k] = v
    return pl

class RegBayesianGmm(BayesianGaussianMixture):
    """ Wrapper for bGMM that sets a higher reg. param. """
    def __init__(self, *args, **kwargs):
        super(RegBayesianGmm, self).__init__(*args, reg_covar = 5*10**-4,
                                             **kwargs)

def findKnee(values):
    # source: https://dataplatform.cloud.ibm.com/analytics/notebooks/54d79c2a-f155-40ec-93ec-ed05b58afa39/view?access_token=6d8ec910cf2a1b3901c721fcb94638563cd646fe14400fecbb76cea6aaae2fb1
    #get coordinates of all the points
    nPoints = len(values)
    allCoord = np.vstack((range(nPoints), values)).T

    # get the first point
    firstPoint = allCoord[0]
    # get vector between first and last point - this is the line
    lineVec = allCoord[-1] - allCoord[0]
    lineVecNorm = lineVec / np.sqrt(np.sum(lineVec**2))

    # find the distance from each point to the line:
    # vector between all points and first point
    vecFromFirst = allCoord - firstPoint

    # To calculate the distance to the line, we split vecFromFirst into two 
    # components, one that is parallel to the line and one that is perpendicular 
    # Then, we take the norm of the part that is perpendicular to the line and 
    # get the distance.
    # We find the vector parallel to the line by projecting vecFromFirst onto 
    # the line. The perpendicular vector is vecFromFirst - vecFromFirstParallel
    # We project vecFromFirst by taking the scalar product of the vector with 
    # the unit vector that points in the direction of the line (this gives us 
    # the length of the projection of vecFromFirst onto the line). If we 
    # multiply the scalar product by the unit vector, we have vecFromFirstParallel
    scalarProduct = np.sum(vecFromFirst * mlb.repmat(lineVecNorm, nPoints, 1), axis=1)
    vecFromFirstParallel = np.outer(scalarProduct, lineVecNorm)
    vecToLine = vecFromFirst - vecFromFirstParallel

    # distance to line is the norm of vecToLine
    distToLine = np.sqrt(np.sum(vecToLine ** 2, axis=1))

    # knee/elbow is the point with max distance value
    idxOfBestPoint = np.argmax(distToLine)

#     print ("Knee of the curve is at index =",idxOfBestPoint)
#     print ("Knee value =", values[idxOfBestPoint])
    return idxOfBestPoint

class MlPipeline(object):
    """ The pipeline. """
    def __init__(self, nStages):
        # function to apply in each stage. 
        self.stageType = [None for n in range(nStages)]
        # inputs to each stage. X is overwritten by previous stage, 
        # all other parameters are carried over. 
        self.stageArgs = [{} for n in range(nStages)] 
        self.finalOut = None
    
    def setX(self, X):
        """ Set X from loaded data """
        maxX = np.max(X) # global normalization.
        X = X / maxX
        self.stageArgs[0]["X"] = X        
        return

    def loadRaw(self, inputFn):
        """ Load a .raw (csv) from RawData dir """
        X = parsing.parseSwitchTrace(inputFn)
        X = np.array(X)
        # maxX = np.array([np.max(X[:, i]) for i in range(4)])
        maxX = np.max(X) # global normalization.
        X = X / maxX
        print ("inputs[0] (original input) loaded (shape: %s)"%str(X.shape))
        self.stageArgs[0]["X"] = X
        self.stageArgs[0]["trace"] = inputFn
        
    def runStages(self):
        for sIdx, s in enumerate(self.stageType):
            if (s == None):
                print ("stage %s not set!"%sIdx)
                return
        for sIdx, s in enumerate(self.stageType):
            # run stage, get output.
            outDict = s(self.stageArgs[sIdx])             
            # populate dictionary for next stage. 
            if (sIdx +1 == len(self.stageType)):
                self.finalOut = {k:v for k, v in outDict.items()}
                self.finalOut['X_orig'] = self.stageArgs[0]['X']
            else:
                for arg, val in outDict.items():
                    if arg not in self.stageArgs[sIdx+1]: # only add items not already there.
                        self.stageArgs[sIdx+1][arg] = val
        if ("Y" in self.finalOut):
            Y = self.finalOut["Y"]
            clusterCt = len(set(Y))
            print ("got Y vector in final output stage for %s items in %s clusters"%(len(Y), clusterCt))

# STAGE ENGINES.
def Project(inpDict):
    X = inpDict["X"]
    projectFcn, n_dim = inpDict["projectFcn"], inpDict["n_dim"]
    Xp = projectFcn(X, n_dim)
    outDict = {k:v for k, v in inpDict.items()}
    outDict["X"] = Xp
    return outDict

# can a scoring function return a vector for all Ks instead of a single score?
# need to pass the cluster function _to_ the scoring function.
def SelectK(inpDict):
    X = inpDict['X']
    clusterFcn, scoreFcn = inpDict["scoreClusterFcn"], inpDict["scoreFcn"]
    kRange, nTrials = inpDict["kRange"], inpDict["nTrials"]
    nInit = inpDict['n_init_search']
    scores, kOpt = scoreFcn(X, clusterFcn, kRange, nTrials, nInit)
    outDict = {k:v for k, v in inpDict.items()}
    outDict["scores"] = scores
    outDict["k"] = kOpt
    return outDict

def Cluster(inpDict):
    """ Cluster and report Y """
    X, clusterFcn = inpDict["X"], inpDict["clusterFcn"]
    k, n_init = inpDict["k"], inpDict['n_init']
    random_state = 1
    clf = clusterFcn(n_components = k, n_init = n_init, random_state = random_state)
    clf.fit(X)
    Y = clf.predict(X)
    outDict = {k:v for k, v in inpDict.items()}
    outDict['Y'] = Y
    return outDict

def scoreBicKnee(X, clusterFcn, kRange, nTrials, nInit):
    """ Calculate BIC score, report k at knee """
    scoreVecs = []
    for t in range(nTrials):
        args = [(X, clusterFcn, k, nInit, t) for k in kRange]
        pool = mp.Pool(1)
        scores = pool.map(scoreBic_inner, args)
        scoreVecs.append(scores)
        pool.close()
    scoreVecs = np.array(scoreVecs)
    kOpt = kRange[findKnee(np.average(scoreVecs, 0))]
    print ("K: %s"%kOpt)
    return scoreVecs, kOpt

def scoreBic_inner(params):
    X, clusterFcn, k, n_init, random_state = params
    # print ("getting BIC score with n_init = %s"%n_init)
    # random_state = random.randint(0, 2**32)
    gmm = clusterFcn(n_components=k, n_init=n_init, random_state = random_state)
    gmm.fit(X)
    return gmm.bic(X)

def pcaProject(X, n_dim):
    """ PCA projection. """
    where_are_NaNs = np.isnan(X)        
    X[where_are_NaNs] = 0
    pca = PCA(n_dim)
    X = pca.fit_transform(X)
    return X

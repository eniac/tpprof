#!/usr/bin/python3
import math


def parseSwitchTrace(filename):
    """
    Parse a file containing network samples.  Assumes one sample per line.
    Different switches are separated by spaces.
    """
    print("parsing input file: %s" % filename)

    switchFeaturesVec = []
    with open(filename, 'r') as data_file:
        for line in data_file:
            tokens = [int(i) for i in line.split()]
            switchFeaturesVec.append(tokens)

    return switchFeaturesVec

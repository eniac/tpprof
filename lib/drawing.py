#!/usr/bin/python3

import argparse
import math
import pickle
import sys
import matplotlib.patches as patches

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import FancyArrowPatch 


LABEL_WIDTH = 1.2
LABEL_HEIGHT = .6
STATE_WIDTH = .9 # width of the per-state heat graphs
STATE_PADDED_WIDTH = 1.0 # width of the per-state heat graphs
STATE_HEIGHT = .9 # width of the per-state heat graphs
STATE_PADDED_HEIGHT = 1.0

Y_PADDING = 0.3 # padding between sequences
POINT_HEIGHT = 1
ORDER_LABEL_OFFSET = 0.15

MAX_SUBSEQUENCE_DISPLAY = 10

def argParser():
    # parse arguments
    parser = argparse.ArgumentParser(
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('infile', type=str, help='The input pickle file.')
    parser.add_argument('--outfile', type=str, help='The output image file.')
    parser.add_argument('--plot', dest='plot', action='store_true',
                        help='whether to open the plot at the end.')
    parser.add_argument('--noplot', dest='plot', action='store_false',
                        help='whether to open the plot at the end.')
    parser.set_defaults(plot=True)
    return parser.parse_args()

def main():
    args = argParser()
    print ("PLOTTER PARAMETERS: ")
    print ("--------------------")
    print ("\tinput file: %s" % args.infile)
    print ("\toutput file: %s" % (args.outfile if args.outfile else "None"))
    print ("\tplot: %s" % ("Yes" if args.plot else "No"))
    print ("--------------------")

    with open(args.infile, 'rb') as handle:
        (X, Y, substring_freq, substring_coverage, totalLen) = pickle.load(handle)
        plot(X, Y, substring_freq, substring_coverage, totalLen)

def plot(original_pts, clustered_pts, merged_freq, coverage_sum,
         outfile, plot = True):
    # compute state frequencies
    state_frequencies = {}

    for state in clustered_pts:
        if state not in state_frequencies:
            state_frequencies[state] = 0
        state_frequencies[state] += 1

    # generate state positioning data structures
    ordered_states = sorted(state_frequencies.items(),
                            key = lambda tup : tup[1])[::-1]
    state_to_position = {val[0]:key for (key, val) in enumerate(ordered_states)}

    # generate sequence positioning data structures
    ordered_sequences = sorted(coverage_sum.items(),
                               key = lambda tup : tup[1])[::-1]

    # Set up the canvas.
    # y starts at the top of the canvas and decrements each time a node gets plotted.
    max_x = LABEL_WIDTH + len(state_to_position) * STATE_PADDED_WIDTH
    max_y = STATE_HEIGHT
    for i in range(0, min(MAX_SUBSEQUENCE_DISPLAY, len(ordered_sequences))):
        max_y += Y_PADDING * (len(ordered_sequences[i][0]) + 1)
    fig = plt.figure(figsize = (max_x, max_y))
    ax = plt.gca()

    # label axes. 
    label_axes(max_y)
    # render states at the top of the canvas.
    render_clustered_states(original_pts, clustered_pts, ordered_states, max_y)

    # render each sequence.
    min_y = render_subsequences(state_to_position, ordered_sequences,
                                ax, max_y, float(len(clustered_pts)))

    # adjust plot and save.
    plt.axis('off')
    plt.xlim(0, max_x)
    plt.ylim((min_y, max_y + LABEL_HEIGHT + STATE_PADDED_HEIGHT))
    plt.savefig(outfile, bbox_inches="tight")

    if plot:
        plt.show()
    else:
        plt.clf()

def label_axes(max_y):
    # render text.
    plt.text(0, max_y + STATE_PADDED_HEIGHT, "% time:\nstability:")

def render_clustered_states(original_pts, clustered_pts, ordered_states, max_y):
    # render heatmaps of clusters found by the algorithm
    # TODO: why 8?
    max_sample = max(np.max(original_pts, 0) * 8.0)
    # print(max_sample)

    original_pts = np.array(original_pts)
    clustered_pts = np.array(clustered_pts)
    # generate a PNG image for each cluster.
    for idx, (state_id, state_freq) in enumerate(ordered_states):
        # select all the samples that belong to this cluster.
        clustered_sample_idx = np.where(clustered_pts == state_id)[0]
        original_sample = original_pts[clustered_sample_idx]

        # calculate the heatmap grid: get average, normalize, and reshape into a
        # 2x2 grid.
        average_sample = np.average(original_sample, 0) * 8.0
        average_sample = average_sample / max_sample
        average_hm = np.flip(np.split(average_sample, 2), 0)

        # render the grid to the appropriate place in the canvas
        left = LABEL_WIDTH + idx * STATE_PADDED_WIDTH
        right = left + STATE_WIDTH
        bottom = max_y
        top = bottom + STATE_HEIGHT

        plt.imshow(average_hm, aspect = 'equal', interpolation = 'nearest',
                   extent = (left, right, bottom, top), cmap = "Greys",
                   vmin = 0, vmax = 1)
        # surround with rectangle.
        ax = plt.gca()
        rect = patches.Rectangle((left, bottom), STATE_WIDTH, STATE_HEIGHT,
                                 linewidth = 1, edgecolor = 'k',
                                 facecolor = 'none')
        ax.add_patch(rect)
        rect = patches.Rectangle((left, bottom), STATE_WIDTH/2, STATE_HEIGHT/2,
                                 linewidth = 0.25, edgecolor = 'k',
                                 facecolor = 'none')
        ax.add_patch(rect)
        rect = patches.Rectangle((left, bottom+STATE_HEIGHT/2), STATE_WIDTH/2,
                                 STATE_HEIGHT/2, linewidth = 0.25,
                                 edgecolor = 'k', facecolor = 'none')
        ax.add_patch(rect)
        rect = patches.Rectangle((left+STATE_WIDTH/2, bottom), STATE_WIDTH/2,
                                 STATE_HEIGHT/2, linewidth = 0.25,
                                 edgecolor = 'k', facecolor = 'none')
        ax.add_patch(rect)
        rect = patches.Rectangle((left+STATE_WIDTH/2, bottom+STATE_HEIGHT/2),
                                 STATE_WIDTH/2, STATE_HEIGHT/2,
                                 linewidth = 0.25, edgecolor = 'k',
                                 facecolor = 'none')
        ax.add_patch(rect)

        # calculate frequency and stability
        freq = len(clustered_sample_idx) / float(len(clustered_pts))

        selfCt = 0
        selfLoopCt = 0
        for i in range(len(clustered_pts) - 1):
            if (clustered_pts[i] == state_id):
                selfCt += 1
                if (clustered_pts[i+1] == state_id):
                    selfLoopCt += 1
        stab = float(selfLoopCt) / float(selfCt)

        plt.text(left + STATE_PADDED_WIDTH/2, max_y + STATE_PADDED_HEIGHT,
                 str(round(freq * 100, 1)) + "%\n" + \
                 str(round(stab * 100, 1)) + "%",
                 horizontalalignment = "center")


def render_subsequences(state_to_position, ordered_sequences, ax, max_y,
                        total_length):
    # render sequences. Each state is represented by a point.
    current_y = max_y
    first = True

    counter = 0

    for subsequence, coverage in ordered_sequences:
        if not first:
            plt.axhline(current_y, color = "k", linewidth = 1, linestyle = "--",
                        antialiased = False)

        current_y -= Y_PADDING

        top_y = current_y
        X, X_unstable, X_stable = [], [], []
        Y, Y_unstable, Y_stable = [], [], []
        for sample, logcount in subsequence:
            x = LABEL_WIDTH + state_to_position[sample] * STATE_PADDED_WIDTH \
                + STATE_WIDTH / 2
            y = current_y
            X.append(x)
            Y.append(y)

            if logcount:
                X_stable.append(x)
                Y_stable.append(y)
                plt.text(x + ORDER_LABEL_OFFSET, y,
                         "O(" + str(int(math.pow(10, logcount - 1))) + ")",
                         verticalalignment = "center")
            else:
                X_unstable.append(x)
                Y_unstable.append(y)

            current_y -= Y_PADDING

        current_y += Y_PADDING
        coverage_pct = coverage / total_length
        plt.text(0, float(top_y + current_y) / 2,
                 str(round(coverage_pct * 100, 1)) + '%',
                 verticalalignment = "center")
        if first:
            # hack to get coverage to show up above the first coverage number
            plt.text(0, float(top_y + current_y) / 2,
                     "cover:\n\n", verticalalignment = "center")
            first = False

        # render any lines
        plt.plot(X, Y, color = "k")
        # render any arrows
        drawArrow(X, Y, ax, 1)
        # render repetition states
        plt.scatter(X_stable, Y_stable, marker = "o", color = "k")
        # render non-repetition states
        plt.scatter(X_unstable, Y_unstable, marker = "o", color = "k",
                    facecolors="none")

        current_y -= Y_PADDING

        counter += 1
        if counter >= MAX_SUBSEQUENCE_DISPLAY:
            break

    return current_y

def drawArrow(x,y,ax,n):
    # draw an arrow leading to every point in a sequence
    for i in range(1, len(x)):
        ar = FancyArrowPatch((x[i-1],y[i-1]),(x[i],y[i]), 
                             arrowstyle='->', mutation_scale=20)
        ax.add_patch(ar)

if __name__ == '__main__':
    args = argParser()

    main()

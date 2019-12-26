#!/usr/bin/python3

import argparse
from collections import defaultdict
import heapq
import math
import numpy as np
from operator import itemgetter
import pickle
import sys


def score_total_coverage(sequence, max_subseq_len, min_frequency_thresh):
    subsequence_freq, subsequence_coverage, taken_ranges = \
            get_subsequences(sequence, max_subseq_len, min_frequency_thresh)

    prev_end = -1
    total_coverage = 0
    for start, end in taken_ranges:
        if start > prev_end:
            total_coverage += (end - start + 1)
        else:
            total_coverage += (end - prev_end)
        prev_end = end

    return subsequence_freq, subsequence_coverage, total_coverage


# ===================================
# =           sequencing.           =
# ===================================

# A bunch of optimizations:
#   numpy sequence for fast slicing
#   to_byte for fast immutability
#   defaultdict is somehow faster, but using its features is slower...
#   taken_candidate skip-ahead to not iterate through obvious taken ranges
#@profile
def get_subsequences(sequence, max_subseq_len, min_frequency_thresh):
    sequence = np.array(sequence, dtype=np.dtype('B'))
    taken_ranges = [] # sorted (by starting index) list of everything
    subsequence_freq = dict()
    subsequence_coverage = dict()

    # for every possible subsequence length (largest to smallest)
    # target_length = subsequence length
    for target_length in range(max_subseq_len, 1, -1):
        if target_length % 100 == 0:
            print('CHECKPOINT: ' + str(target_length))

        subsequence_candidates = defaultdict(list)
        new_taken = [] 
        taken_index = 0
        taken_candidates = [] # Heap => current set of overlapping ranges

        # check every subseq starting from 0
        start_index = 0
        while start_index < len(sequence) - target_length + 1:
            end_index = start_index + target_length

            # if this is completely contained in a larger subseq, ignore
            while taken_index < len(taken_ranges) and \
                  taken_ranges[taken_index][0] <= start_index:
                heapq.heappush(taken_candidates, taken_ranges[taken_index][1])
                taken_index += 1
            while taken_candidates and taken_candidates[0] < end_index:
                heapq.heappop(taken_candidates)
            if taken_candidates:
                # skip ahead
                start_index = taken_candidates[0] - target_length + 1
                continue

            # create the key.  numpy is really good at slicing and converting
            key = sequence[start_index:end_index:1].tobytes()

            if key not in subsequence_candidates:
                # 1st instance of subsequence. Leave for now.
                subsequence_candidates[key] = [(start_index, end_index)]
            elif len(subsequence_candidates[key]) + 1 < min_frequency_thresh:
                # still not above the min_frequency_thresh. Leave for now.
                subsequence_candidates[key].append((start_index, end_index))
            elif len(subsequence_candidates[key]) + 1 == min_frequency_thresh:
                # we just hit the threshold! Take care of it.
                subsequence_candidates[key].append((start_index, end_index))
                new_taken.extend(subsequence_candidates[key])

                subsequence_coverage[key] = subsequence_candidates[key]
                subsequence_freq[key] = min_frequency_thresh
            else:
                # already past the threshold. Take care of it.
                new_taken.append((start_index, end_index))
                subsequence_coverage[key].append((start_index, end_index))
                subsequence_freq[key] += 1

            start_index += 1


        taken_ranges.extend(new_taken)
        taken_ranges.sort(key=lambda tup: tup[0])


    # convert back to tuples
    no_np_subsequence_freq = {}
    no_np_subsequence_coverage = {}
    for k, v in subsequence_freq.items():
        no_np_key = tuple(np.frombuffer(k, dtype = sequence.dtype))
        no_np_subsequence_freq[no_np_key] = v
        no_np_subsequence_coverage[no_np_key] = subsequence_coverage[k]

    return no_np_subsequence_freq, no_np_subsequence_coverage, taken_ranges

def merge_stable(substring_freq, substring_coverage):
    merged_freq = dict()
    merged_coverage = dict()

    # merge substrings of the form ABBA, ABBBA, ABBBBBA -> AB[O(1)]A
    # note that ABA -> AB[O(0)]
    for key, value in substring_freq.items():
        new_key = []
        current = key[0]
        count = 1

        for i in range(1, len(key)):
            if (key[i] == current):
                count += 1
            else:
                new_key.append((current, int(math.ceil(math.log10(count)))))
                current = key[i]
                count = 1

        new_key.append((current, int(math.ceil(math.log10(count)))))

        hashable_new_key = tuple(new_key)
        if hashable_new_key not in merged_freq:
            merged_freq[hashable_new_key] = value
            merged_coverage[hashable_new_key] = substring_coverage[key]
        else:
            merged_freq[hashable_new_key] += value
            merged_coverage[hashable_new_key].extend(substring_coverage[key])

    # converts from a list of coverages to a single number representing the
    # number of unique states covered
    coverage_sum = dict()
    for key, range_list in merged_coverage.items():
        range_list = sorted(range_list, key=itemgetter(0))
        prev_end = -1
        total = 0
        for start, end in range_list:
            if start > prev_end:
                total += (end - start + 1)
            else:
                total += (end - prev_end)
            prev_end = end

        coverage_sum[key] = total

    return merged_freq, coverage_sum

# ======  End of sequencing.  =======

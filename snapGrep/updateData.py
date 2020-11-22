import argparse

def argParser():
    parser = argparse.ArgumentParser(
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('datafile', type=str, help='The raw data file.')
    parser.add_argument('outfile', type=str, help='The output file.')
    return parser.parse_args()

def main():
    args = argParser()

    datafile = open(args.datafile, 'r')

    outfile = open(args.outfile, 'w')

    counter = 0
    for line in datafile:
        row = line.split()

        counter += 1
        outfile.write(str(counter) + ',' + str(len(row)) + ',' + ','.join(row) + '\n')


    datafile.close()
    outfile.close


if __name__ == '__main__':
    main()
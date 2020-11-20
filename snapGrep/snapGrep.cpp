// Minimal snapgrep implementation using hyperScan

// compile: gcc -o snapGrep snapGrep.c --cflags --libs libhs

// # g++ -std=c++11 -o snapGrep snapGrep.cpp $(pkg-config --cflags --libs libhs)

#include <cmath> 
#include <numeric>
#include <cstring>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>
#include <deque>
#include <algorithm>
#include <iterator>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>
#include <iostream>
#include <limits>


// Hyperscan.
#include <hs.h>

// CSV parser.
#include "csvparser.h"

// #define DEBUG
#define REPORTMATCH

// ./snapGrep 4 imbalance.states imbalance.pattern < imbalance_3.csv 

using std::cerr;
using std::cout;
using std::endl;
using std::ifstream;
using std::string;
using std::vector;
using std::cin;
using std::cout;
using std::unordered_map;
using std::deque;


// When a match occurs, send a character outside 
// of the pattern language to prevent overlaps.
bool doBreak = true;
int numBreaksAdded = 0; // Need to keep track for indexing.
char * breakChar = "-";

int matchCount = 0; // Not really used.
int numSwitches = 0;

// function defs.
static void parseFile(const char *filename, vector<string> &patterns,
                      vector<unsigned> &flags, vector<unsigned> &ids);
static void databasesFromFile(const char *filename,
                              hs_database_t **db_streaming,
                              hs_database_t **db_block);
static hs_database_t *buildDatabase(const vector<const char *> &expressions,
                                    const vector<unsigned> flags,
                                    const vector<unsigned> ids,
                                    unsigned int mode);
static unsigned parseFlags(const string &flagsStr);
static
int onMatch(unsigned int id, unsigned long long from, unsigned long long to,
            unsigned int flags, void *ctx);
vector<double> parseRecRow(const CSVRow& row);
void parseTargetState(const CSVRow& row);

// Pretty-print vector.
template<typename T>
std::ostream & operator<<(std::ostream & os, std::vector<T> vec)
{
    os<<"{ ";
    std::copy(vec.begin(), vec.end(), std::ostream_iterator<T>(os, " "));
    os<<"}";
    return os;
}


double hamming_distance(vector<double> a, vector<double> b) {
    double disti = 0;
    for(int i=0; i<a.size(); i++) {
    	disti += fabs(a[i] - b[i]);
    }
    return 1.0*disti/a.size();
}

// Map from state vec to state symbol.
vector<vector<double> > targetStateList;
vector<char> targetStateSymbols;

// Buffer of match similarities for past symbols.
#define MAX_SYMBOL_BUF 1000000
deque<double> symbolMatchBuf;
uint32_t streamOffset = 0;

/*===========================================
=            Hyperscan metadata.            =
===========================================*/

// Hyperscan compiled database (streaming mode)
hs_database_t *db_streaming, *db_block;
// Hyperscan temporary scratch space (used in both modes)
hs_scratch_t *scratch = NULL;
// Vector of Hyperscan stream state (used in streaming mode)
vector<hs_stream_t *> streams;
// Error flag.
hs_error_t err;
/*=====  End of Hyperscan metadata.  ======*/

int main(int argc, char *argv[])
{
	// Parameters: 
    // 1: number of features (switches) in input csv
	// 2: target state
	// 3: pattern (regex)
	if (argc != 4){
		cout << "invalid arguments. Usage: snapGrep numSwitches signature.states signature.patterns" << endl;
	}

    numSwitches = std::stoi(argv[1]);
    cout << "expecting files with " << numSwitches << " switches in each samples" << endl;
	// Read state definitions.
	const char *targetStateFile = argv[2];
	std::ifstream file(targetStateFile);
	CSVRow row;
	while(file >> row) {
    	parseTargetState(row);
    }

    cout << "loaded " << targetStateList.size() << " target states" << endl;
    for (int i = 0; i < targetStateList.size(); i++){
    	cout << "\tState symbol: " << targetStateSymbols[i] << " utilization vector: " << targetStateList[i] << std::endl;
    }

	// Read pattern and load into hyperscan.
    const char *patternFile = argv[3];
    cout << "Pattern file: " << patternFile << endl;
    databasesFromFile(patternFile, &db_streaming, &db_block);

    // setup hyperscan.
    // Allocate scratch.
    err = hs_alloc_scratch(db_streaming, &scratch);
    if (err != HS_SUCCESS) {
        cerr << "ERROR: could not allocate scratch space. Exiting." << endl;
        exit(-1);
    }
    // open the stream. 
    cout << "opening stream" << endl;
    hs_stream_t *streamId;
    err = hs_open_stream(db_streaming, 0, &streamId);
    if (err != HS_SUCCESS) {
        cerr << "ERROR: Unable to open stream. Exiting." << endl;
        exit(-1);
    }

    int counter = 0;
    while (cin >> row){
	    // read snapshot from input.
    	vector<double> snapshotVec = parseRecRow(row);
        #ifdef DEBUG
    	cout << "read snapshot: " << snapshotVec << endl;
        #endif
    	// Scan through states to find the nearest neighbor.
    	// This can be optimized with specialized data structures.
    	char nearestSymbol[2] = {0};
    	double nearestDist = std::numeric_limits<double>::max();
    	for (int i = 0; i < targetStateList.size(); i++){
    		auto dist = hamming_distance(snapshotVec, targetStateList[i]);
      //       cout << "\t" << targetStateList[i] << endl;
    		// cout << "\t" << targetStateSymbols[i] << " : " << dist << endl;
    		if (dist < nearestDist){
    			nearestDist = dist;
    			nearestSymbol[0] = targetStateSymbols[i];
    		}
    	}
        #ifdef DEBUG
        // cout << "counter: " << counter << endl;
        // counter ++;
    	cout << "\tsymbol: " << nearestSymbol << " dist: " << nearestDist << endl;
        #endif
    	// push a similarity score to buffer.
        // TODO: adjust this for normalized.
    	symbolMatchBuf.push_back(1.0/(1.0-nearestDist));
    	// Remove the earliest similarity score if the buffer is full.
    	if (symbolMatchBuf.size() > MAX_SYMBOL_BUF){
    		symbolMatchBuf.pop_front();
    	}
    	// update the scan.
	    // Inject the break character to prevent overlapping matches.
	    if (doBreak){
		    err = hs_scan_stream(streamId,breakChar, 1, 0, scratch, onMatch, &matchCount);
            if (err != HS_SUCCESS) {
                cerr << "ERROR scanning." << endl;
                exit(-1);
            }
            numBreaksAdded ++;
		    doBreak = false;
	    }
	    // add the new state symbol to this scan.
	    err = hs_scan_stream(streamId, nearestSymbol, 1, 0, scratch, onMatch, &matchCount);
        if (err != HS_SUCCESS) {
            cerr << "ERROR scanning." << endl;
            exit(-1);
        }

    }
    // input file is done. Close the stream.
    // close the stream.
    cout << "closing stream" << endl;
    err = hs_close_stream(streamId, scratch, onMatch, &matchCount);
    hs_free_scratch(scratch);
    return 0;
}

// Match event handler: called every time Hyperscan finds a match.
static
int onMatch(unsigned int id, unsigned long long from, unsigned long long to,
            unsigned int flags, void *ctx) {
    // Our context points to a size_t storing the match count
    size_t *matches = (size_t *)ctx;
    (*matches)++;
    doBreak = true;
    double matchScore = 0;
    for (int i = from; i < to; i++){
    	matchScore += symbolMatchBuf[i + streamOffset - numBreaksAdded];
    }
    matchScore = matchScore / float(to - from); // Normalize by pattern length.
    #ifdef REPORTMATCH
    cout << "MATCH in range: " << from- numBreaksAdded << " - " << to- numBreaksAdded << " score: " << matchScore << endl;
    #endif
    return 0; // continue matching
}



// Simple timing class
class Clock {
public:
    void start() {
        time_start = std::chrono::system_clock::now();
    }

    void stop() {
        time_end = std::chrono::system_clock::now();
    }

    double seconds() const {
        std::chrono::duration<double> delta = time_end - time_start;
        return delta.count();
    }
private:
    std::chrono::time_point<std::chrono::system_clock> time_start, time_end;
};


static hs_database_t *buildDatabase(const vector<const char *> &expressions,
                                    const vector<unsigned> flags,
                                    const vector<unsigned> ids,
                                    unsigned int mode) {
    hs_database_t *db;
    hs_compile_error_t *compileErr;
    hs_error_t err;

    Clock clock;
    clock.start();
    err = hs_compile_multi(expressions.data(), flags.data(), ids.data(),
                           expressions.size(), mode, nullptr, &db, &compileErr);

    clock.stop();

    if (err != HS_SUCCESS) {
        if (compileErr->expression < 0) {
            // The error does not refer to a particular expression.
            cerr << "ERROR: " << compileErr->message << endl;
        } else {
            cerr << "ERROR: Pattern '" << expressions[compileErr->expression]
                 << "' failed compilation with error: " << compileErr->message
                 << endl;
        }
        // As the compileErr pointer points to dynamically allocated memory, if
        // we get an error, we must be sure to release it. This is not
        // necessary when no error is detected.
        hs_free_compile_error(compileErr);
        exit(-1);
    }

    cout << "Hyperscan " << (mode == HS_MODE_STREAM ? "streaming" : "block")
         << " mode database compiled in " << clock.seconds() << " seconds."
         << endl;

    return db;
}




/**
 * This function will read in the file with the specified name, with an
 * expression per line, ignoring lines starting with '#' and build a Hyperscan
 * database for it.
 */
static void databasesFromFile(const char *filename,
                              hs_database_t **db_streaming,
                              hs_database_t **db_block) {
    // hs_compile_multi requires three parallel arrays containing the patterns,
    // flags and ids that we want to work with. To achieve this we use
    // vectors and new entries onto each for each valid line of input from
    // the pattern file.
    vector<string> patterns;
    vector<unsigned> flags;
    vector<unsigned> ids;

    // do the actual file reading and string handling
    parseFile(filename, patterns, flags, ids);

    // Turn our vector of strings into a vector of char*'s to pass in to
    // hs_compile_multi. (This is just using the vector of strings as dynamic
    // storage.)
    vector<const char*> cstrPatterns;
    for (const auto &pattern : patterns) {
        cstrPatterns.push_back(pattern.c_str());
    }

    cout << "Compiling Hyperscan databases with " << patterns.size()
         << " patterns." << endl;

    *db_streaming = buildDatabase(cstrPatterns, flags, ids, HS_MODE_STREAM | HS_MODE_SOM_HORIZON_LARGE);
    *db_block = buildDatabase(cstrPatterns, flags, ids, HS_MODE_BLOCK);
}

static void parseFile(const char *filename, vector<string> &patterns,
                      vector<unsigned> &flags, vector<unsigned> &ids) {
    ifstream inFile(filename);
    if (!inFile.good()) {
        cerr << "ERROR: Can't open pattern file \"" << filename << "\"" << endl;
        exit(-1);
    }

    for (unsigned i = 1; !inFile.eof(); ++i) {
        string line;
        getline(inFile, line);

        // if line is empty, or a comment, we can skip it
        if (line.empty() || line[0] == '#') {
            continue;
        }

        // otherwise, it should be ID:PCRE, e.g.
        //  10001:/foobar/is

        size_t colonIdx = line.find_first_of(':');
        if (colonIdx == string::npos) {
            cerr << "ERROR: Could not parse line " << i << endl;
            exit(-1);
        }

        // we should have an unsigned int as an ID, before the colon
        unsigned id = std::stoi(line.substr(0, colonIdx).c_str());

        // rest of the expression is the PCRE
        const string expr(line.substr(colonIdx + 1));

        size_t flagsStart = expr.find_last_of('/');
        if (flagsStart == string::npos) {
            cerr << "ERROR: no trailing '/' char" << endl;
            exit(-1);
        }

        string pcre(expr.substr(1, flagsStart - 1));
        string flagsStr(expr.substr(flagsStart + 1, expr.size() - flagsStart));
        unsigned flag = parseFlags(flagsStr);

        patterns.push_back(pcre);
        flags.push_back(flag);
        ids.push_back(id);
    }
}

static unsigned parseFlags(const string &flagsStr) {
    unsigned flags = HS_FLAG_SOM_LEFTMOST;
    for (const auto &c : flagsStr) {
        switch (c) {
        case 'i':
            flags |= HS_FLAG_CASELESS; break;
        case 'm':
            flags |= HS_FLAG_MULTILINE; break;
        case 's':
            flags |= HS_FLAG_DOTALL; break;
        case 'H':
            flags |= HS_FLAG_SINGLEMATCH; break;
        case 'V':
            flags |= HS_FLAG_ALLOWEMPTY; break;
        case '8':
            flags |= HS_FLAG_UTF8; break;
        case 'W':
            flags |= HS_FLAG_UCP; break;
        case '\r': // stray carriage-return
            break;
        default:
            cerr << "Unsupported flag \'" << c << "\'" << endl;
            exit(-1);
        }
    }
    return flags;
}


void parseTargetState(const CSVRow& row) {
  // Parse a snapshot record, return a vector of doubles.
  // Format: num entries, state symbol, switch 1 value, switch 2 value, switch 3 value, switch 4 value, ...
  auto stateSymbol = string(row[0]);
  vector<double> outVec;
  for (int i = 0; i < numSwitches; i++){
	  auto val = (double) (std::stof(row[i+1]));
      val = val / (1000000000.0);
	  outVec.push_back(val);
  }
  targetStateList.push_back(outVec);
  targetStateSymbols.push_back(stateSymbol.c_str()[0]);
  return;
}


vector<double> parseRecRow(const CSVRow& row) {
  // Parse a snapshot record, return a vector of doubles.
  // Format: num entries, switch 1 value, switch 2 value, switch 3 value, switch 4 value, ...
  auto snapshotId  = (uint32_t) std::stoi(row[0]);
  
  vector<double> outVec;
  for (int i = 0; i < numSwitches; i++){
	  auto val = (double) (std::stof(row[i+1]));
      val = val / (1000000000.0);
	  outVec.push_back(val);
  }
  return outVec;
}


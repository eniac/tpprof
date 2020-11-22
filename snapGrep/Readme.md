### Traffic Pattern Scoring ###

Traffic Pattern Scoring takes input the data and find matches according to the signatures.

## Signatures ##

A traffic pattern signature describes the approximate spatial and temporal characteristics of a traffic pattern.
It has two parts:

- States: Describing the approximate samples observerd. Example is in ```example/signature.states```, where each line desribes the one state. The format is <state_name>, <num_switches>, \<comma seperated switch values\>
- Subsequences: Written as regular expression that estimates how the network transitions between the states during the pattern.
- Examples can be found in ```example``` and ```imbalance``` folder.

## Usage ##

Require hyperscan. It can be installed from [here](https://github.com/intel/hyperscan).
After hyperscan is working:

```
make
python3 updateData.py <input_data> <new_format_data>
./snapGrep <num_switches> <signatures> <pattern> <new_format_data>
```
- Outputs matches and score on command line.
- The data formar is different than the one data in folder. We have a simple script, ```snapGrep/updateData.py```, to change format accordingly.
- For detail, please refer to the readme file in ```snapGrep``` folder or section 6 of the [paper](https://www.usenix.org/system/files/nsdi20-paper-yaseen.pdf).
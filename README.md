### tpprof ###

These scripts render state transition sequences from snapshot traces. 
In the sequence plots, filled circles represent *stable states* that repeated 2 or more times. 
Unfilled circles represent *unstable states* that did not repeat.

#### Installation ####

Run `install.sh`

#### Usage ####

```python3 ./tpprof.py <input_data>```
- Parses the snapshot trace in *input_data* to generate intermediate results and plots in \<NAME\>.{cluster,subsequence,pdf}
- NAME is automatically set to the concatenation of 'tmp/' and the text between the last '/' and '.' in *input_data*, e.g., ```input_data = data/alexnet.raw``` => ```result_prefix = tmp/alexnet.*```
- tpprof automatically uses existing intermediate results.  If you need to regenerate clustering or sequencing, delete the intermediate files.

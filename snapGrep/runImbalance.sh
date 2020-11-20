# requires hyperscan to be installed.
# https://github.com/intel/hyperscan
echo "building"
make
echo "timing running"
time ./snapGrep 4 imbalance/imbalance_3.states imbalance/imbalance_3.pattern < imbalance/imbalance_3.csv 

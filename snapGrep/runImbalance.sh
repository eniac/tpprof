# requires hyperscan to be installed.
# https://github.com/intel/hyperscan
echo "building"
make
echo "running imbalance example"
./snapGrep 4 imbalance/imbalance_3.states imbalance/imbalance_3.pattern < imbalance/imbalance_3.csv 

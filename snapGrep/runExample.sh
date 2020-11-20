# requires hyperscan to be installed.
# https://github.com/intel/hyperscan
echo "building"
make
echo "running"
./snapGrep 4 signature.states signature.pattern < input.csv 

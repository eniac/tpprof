# requires hyperscan to be installed.
# https://github.com/intel/hyperscan
echo "building"
make
echo "running simple example"
./snapGrep 4 example/signature.states example/signature.pattern < example/input.csv 

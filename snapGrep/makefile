LIBS= -I/usr/local/include/hs -L/usr/local/lib -lhs
CFLAGS = -std=c++14 -O3 
CC = g++

# CFLAGS = -std=c++14 -Ofast -fopt-info-vec-optimized
#-funroll-loops -mprefer-vector-width=512 -march=skylake-avx512 -fopt-info-vec-optimized #-mavx512f -mavx512dq -mavx512bw -mavx512vbmi -mavx512vbmi2 -mavx512vl

objects = snapGrep
all: $(objects)

$(objects): %: %.cpp
	$(CC) -o $@ $< $(LIBS) $(CFLAGS)

clean: 
	rm  $(objects)
CXXFLAGS += -O3
#CXXFLAGS += -g
CXXFLAGS += -std=c++11 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64
CXXFLAGS += -I../../../libosmium/include

OS:=$(shell uname -s)
ifeq ($(OS),Darwin)
CXXFLAGS += -stdlib=libc++
LDFLAGS += -stdlib=libc++
endif

CXXFLAGS_WARNINGS := -Wall -Wextra -pedantic -Wredundant-decls -Wdisabled-optimization -Wctor-dtor-privacy -Wnon-virtual-dtor -Woverloaded-virtual -Wsign-promo -Wold-style-cast

LIB_EXPAT := -lexpat
LIB_PBF := -pthread -lz -lprotobuf-lite -losmpbf
LIB_GZIP := -lz
LIB_BZIP2 := -lbz2

LIB_IO := $(LIB_EXPAT) $(LIB_PBF) $(LIB_GZIP) $(LIB_BZIP2)

all:

osm2wkt: osm2wkt.cc
	$(CXX) $(CXXFLAGS) $(CXXFLAGS_WARNINGS) -o $@ $< $(LDFLAGS) $(LIB_IO)

scenarios: osm2wkt

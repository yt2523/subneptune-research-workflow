#DEBUG=-g
CC=g++ #-fopenmp

CFLAGS= -std=c++0x -O3 -Wall #-I ~/Downloads/gsl/include
LDFLAGS= -L/usr/local/lib -lgsl -lgslcblas -lm #-L ~/Downloads/gsl/lib

SRCDIR = src
LIBDIR = src

BIN = planet
SOURCES := $(wildcard $(SRCDIR)/*.cpp)
OBJ := $(patsubst $(SRCDIR)/%,%,$(SOURCES))
OBJ := $(patsubst %.cpp,%.o,$(OBJ))
OBJ := $(addprefix ./$(LIBDIR)/,$(OBJ))

planet: $(OBJ)
	$(CC) -o $@ $^ $(LDFLAGS) $(DEBUG)

$(LIBDIR)/%.o: $(SRCDIR)/%.cpp  
	$(CC) -o $@ -c $< $(CFLAGS) $(DEBUG)

clean:
	rm -f *.o ./src/*.o planet

test-tp-profile: src/tp_profile.cpp tests/test_tp_profile.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -Wall -Isrc -o tests/.build/test-tp-profile src/tp_profile.cpp tests/test_tp_profile.cpp
	tests/.build/test-tp-profile tests/.build

test-tp-settings: src/tp_settings.cpp src/parser.cpp tests/test_tp_settings.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -Wall -Isrc -o tests/.build/test-tp-settings src/tp_settings.cpp src/parser.cpp tests/test_tp_settings.cpp
	tests/.build/test-tp-settings tests/.build

.PHONY: test-tp-profile test-tp-settings

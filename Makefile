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

test-tp-hydro: src/hydro.cpp src/EOS.cpp src/EOSlist.cpp src/phase.cpp src/tp_profile.cpp src/tp_stepper.cpp tests/test_tp_hydro.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -Wall -Isrc -o tests/.build/test-tp-hydro src/hydro.cpp src/EOS.cpp src/EOSlist.cpp src/phase.cpp src/tp_profile.cpp src/tp_stepper.cpp tests/test_tp_hydro.cpp $(LDFLAGS)
	tests/.build/test-tp-hydro tests/.build

.PHONY: test-tp-profile test-tp-settings test-tp-hydro test-tp-knots test-tp-constructors

test-tp-knots: src/hydro.cpp src/EOS.cpp src/EOSlist.cpp src/phase.cpp src/tp_profile.cpp src/tp_stepper.cpp tests/test_tp_knots.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -Wall -Isrc -o tests/.build/test-tp-knots src/hydro.cpp src/EOS.cpp src/EOSlist.cpp src/phase.cpp src/tp_profile.cpp src/tp_stepper.cpp tests/test_tp_knots.cpp $(LDFLAGS)
	tests/.build/test-tp-knots tests/.build

test-tp-constructors: src/hydro.cpp src/EOS.cpp src/EOSlist.cpp src/phase.cpp src/tp_profile.cpp src/tp_stepper.cpp tests/test_tp_constructors.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -Wall -Isrc -o tests/.build/test-tp-constructors src/hydro.cpp src/EOS.cpp src/EOSlist.cpp src/phase.cpp src/tp_profile.cpp src/tp_stepper.cpp tests/test_tp_constructors.cpp $(LDFLAGS)
	tests/.build/test-tp-constructors tests/.build

TP_TEST_SOURCES = src/hydro.cpp src/EOS.cpp src/EOSlist.cpp src/phase.cpp src/tp_profile.cpp src/tp_stepper.cpp

test-tp-edges: tests/test_tp_stepper_edges.cpp src/tp_profile.cpp src/tp_stepper.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -O2 -Isrc tests/test_tp_stepper_edges.cpp src/tp_profile.cpp src/tp_stepper.cpp $(LDFLAGS) -o tests/.build/test-tp-edges
	tests/.build/test-tp-edges tests/fixtures/tp-edge-knots.csv reverse
	tests/.build/test-tp-edges tests/fixtures/tp-edge-knots.csv near
	tests/.build/test-tp-edges tests/fixtures/tp-edge-knots.csv near-offset

test-tp-truncation: $(TP_TEST_SOURCES) tests/test_tp_truncation.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -O2 -Isrc tests/test_tp_truncation.cpp $(TP_TEST_SOURCES) $(LDFLAGS) -o tests/.build/test-tp-truncation
	tests/.build/test-tp-truncation tests/fixtures/tp-truncation-broad.csv

test-tp-callbacks: $(TP_TEST_SOURCES) tests/test_tp_callbacks.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -O2 -DCURRENT_TP -Isrc tests/test_tp_callbacks.cpp $(TP_TEST_SOURCES) $(LDFLAGS) -o tests/.build/test-tp-callbacks
	tests/.build/test-tp-callbacks coverage tests/fixtures/tp-short-coverage.csv
	tests/.build/test-tp-callbacks inner > tests/.build/legacy-inner.log
	tests/.build/test-tp-callbacks outer > tests/.build/legacy-outer.log

.PHONY: test-tp-edges test-tp-truncation test-tp-callbacks

test-tp-diagnostics: $(TP_TEST_SOURCES) src/tp_diagnostics.cpp tests/test_tp_diagnostics.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -O2 -Isrc tests/test_tp_diagnostics.cpp src/tp_diagnostics.cpp $(TP_TEST_SOURCES) $(LDFLAGS) -o tests/.build/test-tp-diagnostics
	tests/.build/test-tp-diagnostics tests/.build

test-tp-checker:
	python3 -B tests/test_tp_checker.py

.PHONY: test-tp-diagnostics test-tp-checker

test-tp-wrong-phase: $(TP_TEST_SOURCES) src/tp_diagnostics.cpp tests/test_tp_wrong_phase.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -O2 -Isrc tests/test_tp_wrong_phase.cpp src/tp_diagnostics.cpp $(TP_TEST_SOURCES) $(LDFLAGS) -o tests/.build/test-tp-wrong-phase
	tests/.build/test-tp-wrong-phase tests/.build

test-tp-cli: planet
	python3 -B tests/test_tp_cli.py

.PHONY: test-tp-wrong-phase test-tp-cli

# Build only: running this precision probe counts as a full solver invocation.
build-tp-off-probe: $(TP_TEST_SOURCES) src/parser.cpp tests/tp_off_probe.cpp
	mkdir -p tests/.build
	$(CC) -std=c++11 -O3 -Wall -Isrc tests/tp_off_probe.cpp $(TP_TEST_SOURCES) src/parser.cpp $(LDFLAGS) -o tests/.build/tp-off-probe

.PHONY: build-tp-off-probe

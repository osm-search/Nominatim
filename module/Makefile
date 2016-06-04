MODULES = nominatim
PG_CPPFLAGS = -I$(MODSRCDIR)
include $(PGXS)

VPATH = $(MODSRCDIR)

all:
	chmod 755 nominatim.so

install:
	@echo Library does not need to be installed.

This is an Example RDL implimentation of an AHCI 1.1 Host Controller interface

This SATA AHCI example has registers common to the base definition and then
registers that are repeated per controller port.  This examples shows how to
code this using Arrays and PERL.

There is a single variable: $NUM_SATA_PORTS which needs to be set at compile time to build
a controller implimentation.

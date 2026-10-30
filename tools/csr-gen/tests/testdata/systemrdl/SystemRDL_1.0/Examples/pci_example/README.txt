This example describes a PCI Type 0 configuration header per the
PCI 3.0 specification.  Every attempt was made to be sure its accurate
but I highly encourage anyone using this to review it further.  The author is
not an expert in the nuances of PCI.

The user would need to OR the hard_reset with the soft_reset signal before feeding
soft_reset back into the CPU slave.

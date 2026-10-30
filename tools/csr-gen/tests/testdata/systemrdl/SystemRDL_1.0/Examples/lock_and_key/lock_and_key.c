/*
 * This contrived example was generated from information present in lock_and_key.xml
 * to show how software can be automatically generated from knowledge that lock.data1
 * is software write-enabled by key.value.
 *
 *  Revision:    $Revision:$
 *  Date:        $Date:$
 *
 *  Copyright (c) 2009 The SPIRIT Consortium.
 *
 *  This work forms part of a deliverable of The SPIRIT Consortium.
 *
 *  Use of these materials are governed by the legal terms and conditions
 *  outlined in the disclaimer available from www.spiritconsortium.org.
 *
 *  This source file is provided on an AS IS basis.  The SPIRIT
 *  Consortium disclaims any warranty express or implied including
 *  any warranty of merchantability and fitness for use for a
 *  particular purpose.
 *
 *  The user of the source file shall indemnify and hold The SPIRIT
 *  Consortium and its members harmless from any damages or liability.
 *  Users are requested to provide feedback to The SPIRIT Consortium
 *  using either mailto:feedback@lists.spiritconsortium.org or the forms at
 *  http: *www.spiritconsortium.org/about/contact_us/
 *
 *  This file may be copied, and distributed, with or without
 *  modifications; this notice must be included on any copy.
 *
 */

/* Register offsets */
#define reg_lock_o 0
#define reg_key_o 4

/* Field value masks */
#define reg_lock_data1_m 0x0000ffffUL
#define reg_lock_data2_m 0xffff0000UL
#define reg_key_value_m 0x00000001UL


void write_reg (char *base, int offset, unsigned long value) 
{
  unsigned long *regaddr;
  unsigned long *keyaddr;
  
  (char *) regaddr = base+offset;
  (char *) keyaddr = base+reg_key_o;
  
  switch (offset) {
  case reg_lock_o:
    *keyaddr |= reg_key_value_m; /* Enable writes for data1 value */
    *regaddr = value;
    *keyaddr &= ~reg_key_value_m; /* Disable writes for data1 value */
    break;

  case reg_key_o:
    *regaddr = (value & reg_key_value_m);
    break;
    
  default:
    break;
  }

  return;
  
}

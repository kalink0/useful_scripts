# Open TODOs

## T325
Table t325 has information it it that show at which time an app was used/open.
There are three different timestamps in it. It is necessary to find out the meanings of them

# T415
Table t415 shows information about data usage.
This could be an information which application used the network.
But the units in the column f004 needs to be verified / we need the meaning of them

# T308
Table t308 contains data of the battery status.
Column f004 contain a long number.
e.g. 1166996447693897789
I've read about available masks to get data out.

PACKED_BATTERY_LEVEL_MASK = 0xffff
PACKED_BATTERY_VOLTAGE_MASK = 0xffff0000
PACKED_BATTERY_TEMPERATURE_MASK = 0xffff00000000
PACKED_BATTERY_HEALTH_MASK = 0xf000000000000
PACKED_BATTERY_STATUS_MASK = 0xf0000000000000
PACKED_BATTERY_PLUG_TYPE_MASK = 0xf00000000000000
PACKED_BATTERY_PRESENT_MASK = 0x7000000000000000

Double CHeck necessary Source is: http://3.87.228.100/wp-content/uploads/2019/04/MLT_Paper.pdf

# auto_vent

This is Arkansas BalloonSAT's attempt to add an autonomous venting feature to the Nationwide Eclipse Ballooning Project's Engineering Track vent payload.
The vent board is connected to the Iridium payload via ZigBee and listens for particular three-character commands. For example, 'ABC' would initiate an IDLE command, 'JKL' initiates the VALVE_OPEN command, etc. This modification to the stock software and hardware consists of a new pressure sensor and modified micropython code to handle triggering the vent state based on pressure.
The April 8, 2024 total solar eclipse mission aims for floating the Engineering track balloons at ~95,000 ft. The vent system when activated at ~80,000 ft should result in a stable float after 10-15 minutes. Given the traffic on the Iridium network on solar eclipse day, this will trigger the vent when the pressure drops to 26 mbar and aims for a steady pressure of ~15 mbar. 
The pressure sensors on the existant vent board have an operating pressure from XXX to XXX. Since the pressures we'll need to start venting at are less than 30 mbar we add a MS5803 module connected to the xbee3 board via I2C. This pressure sensor works at those stratospheric levels so we can more accurately trigger the vent.
In order to program these boards you will need to use XCTU and load the main.py file into the file system. Set the trigger levels in main.py for your situation. We are using 26 mbar to start and aiming for 15 mbar float.
Delete the existing main.py file from the xbee3's file system. Clear the board's memory via AT command (PY E). Load up-to-date main.py file into file system.
Open Python terminal and hit Ctrl+R to load the script. This should give you an indication that it is working. If not, check wiring, I2C pullups, etc. for troubleshooting. Make sure you set PS=1 to auto-load the python script on boot and you should be good to go.

This should work for any of the vent styles (stock MSU, UMD, UMDxMSU, etc.) that use the occams vent board and servo.

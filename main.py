"""
Title: XBEE3 Valve/Vent Unit
Author: Kristoffer Allick
Created: 12/20/2022
Revised:
Target Device: Vent board XBEE3 SMT

Forked by: R. Carroll 1/2024

Incorporated XBee3 micropython code example for xbee3 module interface to MS8607
from https://github.com/eewiki/Xbee3-MicroPython/blob/1a2f5dc80b099c522e679adff1a4310b5239a44a/samples/Zigbee_MS8607_i2c_rev1.py
(need to adapt calculation to other pressure modules, i.e., MS5611. This one currently uses MS5803)

aim here is to trigger balloon venting at fixed pressure and close vent at target pressure
one expected issue here is the trigger needs to be ~26 mbar but the module
only reads down to 10 mbar so instrumental uncertainties there may be an issue

"""

# Imports
import xbee
import machine
from machine import Pin
from machine import I2C
from micropython import const
import time

#Pins
usr_led = Pin(machine.Pin.board.D4, Pin.OUT, value=0)   #Enable pin on XBEE3 set to low initially
asc_led = Pin(machine.Pin.board.D5, Pin.OUT, value=0)   #Enable pin on XBEE3 set to low initially
spkr_pin = Pin(machine.Pin.board.P0, Pin.OUT, value=0)  #Shush chatty monkey
msp_pin = Pin(machine.Pin.board.P7, Pin.OUT)   #Enable pin on XBEE3 set to low initially
heater_pin = Pin(machine.Pin.board.D18, Pin.OUT, value=1)
Hall_pin = Pin(machine.Pin.board.D3, Pin.IN, pull=None)

# list of commands in hex for MS8607 pressure sensor
c_reset = const(0x1E) # reset command 
r_c1 = const(0xA2) # read PROM C1 command
r_c2 = const(0xA4) # read PROM C2 command
r_c3 = const(0xA6) # read PROM C3 command
r_c4 = const(0xA8) # read PROM C4 command
r_c5 = const(0xAA) # read PROM C5 command
r_c6 = const(0xAC) # read PROM C6 command
r_adc = const(0x00) # read ADC command
r_d1 = const(0x48) # convert D1 (OSR=4096)
r_d2 = const(0x58) # convert D2 (OSR=4096)
p_address = 0x76 #pressure sensor i2c address

# list of commands in hex for MS8607 humidity sensor

r_user = const(0xE7) # read user register command
w_user = const(0xE6) # write user register command
t_temp = const(0xE3) # trigger temperature measurement, hold master

# set register format 
REGISTER_FORMAT = '>h' # ">" big endian, "h" 2 bytes
REGISTER_SHIFT = 4 # rightshift 4 for 12 bit resolution

## list of constants for auto_valve functions
## set these to whatever works for your flight
VOlevel = 260.0 #Valve Open trigger at 26 mbar (~80k ft)
VClevel = 150.0 #Valve Close trigger at 15 mbar (~95k ft)
VCtimeout = 15.0 #set a timeout for vent close in case VClevel is not attained within VCtimeout

autovalve = 0

# I2C setup
i2c = I2C(1, freq=100000)
addresses = i2c.scan()
sensor_addr = addresses[0]
print(sensor_addr)



print("Vent Control Initialize")

# reset pressure sensor
def reset_ps():
#   sensor_addr = p_address
  data = bytearray([c_reset])
  i2c.writeto(sensor_addr, data)
  return data

# scan i2c bus for active addresses
def scan_I2C():
  devices = i2c.scan()
  return devices

def read_c1(): #read PROM value C1
  data = bytearray([r_c1])
  i2c.writeto(sensor_addr, data)
  raw_c = i2c.readfrom(sensor_addr, 2) #raw C is 2 bytes
  value = int.from_bytes(raw_c, "big") # use builtin to convert to integer
  return value

def read_c2(): #read PROM value C2
  data = bytearray([r_c2])
  i2c.writeto(sensor_addr, data)
  raw_c = i2c.readfrom(sensor_addr, 2) #raw C is 2 bytes
  value = int.from_bytes(raw_c, "big") # use builtin to convert to unsigned integer
  return value

def read_c3(): #read PROM value C3
  data = bytearray([r_c3])
  i2c.writeto(sensor_addr, data)
  raw_c = i2c.readfrom(sensor_addr, 2) #raw C is 2 bytes
  value = int.from_bytes(raw_c, "big") # use builtin to convert to unsigned integer
  return value

def read_c4(): #read PROM value C4
  data = bytearray([r_c4])
  i2c.writeto(sensor_addr, data)
  raw_c = i2c.readfrom(sensor_addr, 2) #raw C is 2 bytes
  value = int.from_bytes(raw_c, "big") # use builtin to convert to unsigned integer
  return value

def read_c5(): #read PROM value C5
  data = bytearray([r_c5])
  i2c.writeto(sensor_addr, data)
  raw_c = i2c.readfrom(sensor_addr, 2) #raw C is 2 bytes
  value = int.from_bytes(raw_c, "big") # use builtin to convert to unsigned integer
  return value

def read_c6(): #read PROM value C6
  data = bytearray([r_c6])
  i2c.writeto(sensor_addr, data)
  raw_c = i2c.readfrom(sensor_addr, 2) #raw C is 2 bytes
  value = int.from_bytes(raw_c, "big") # use builtin to convert to unsigned integer
  return value
  

# start D1 conversion - pressure (24 bit unsigned)
def start_d1():
  #print ('start D1 ')
  data = bytearray([r_d1])
  i2c.writeto(sensor_addr, data)

# start D2 conversion - temperature (24 bit unsigned)  
def start_d2():
  #print ('start D2 ')
  data = bytearray([r_d2])
  i2c.writeto(sensor_addr, data) 

#read pressure sensor ADC
def read_adc(): #read ADC 24 bits unsigned
  data = bytearray([r_adc])
  i2c.writeto(sensor_addr, data)
  adc = i2c.readfrom(sensor_addr, 3) #ADC is 3 bytes
  value = int.from_bytes(adc, "big") # use builtin to convert to integer
  return value
  

def GetPressure():
    #start on pressure sensor
    ##these 2nd order settings are for the MS5611 module
    start_d1() # start D1 conversion
    time.sleep(1.0) # short delay during conversion
    raw_d1 = read_adc()
    start_d2() # start D2 conversion
    time.sleep(1.0) 
    raw_d2 = read_adc()
    dT = raw_d2 - (C5 * 256) # difference between actual and ref P temp
    Temp = (2000 + (dT * (C6/8388608))) #actual P temperature
    OFF = (C2*65536) + (C4*dT/128) # offset at actual P temperature
    SENS = (C1*32768) + (C3*dT/256) # pressure offset at actual temperature
    Pres = (raw_d1*SENS/2097152 - OFF)/32768 # barometric pressure
    print ('P Temp = ', '%.1fC' % Temp)
    print ('Pressure = ', '%.1f ' % Pres)
    #add second order temperature correction
    #currently this is really clunky. needs to use NumPy?
    T2 = 0
    OFF2 = 0
    SENS2 = 0
    if Temp < 2000.0:
       T2 = (dT**2)/2147483648
       OFF2 = 5*((Temp-2000)**2)/2
       SENS2 = 5*((Temp-2000)**2)/4
    if Temp < -1500.0:
       OFF2 = OFF2+7*((Temp +1500)**2)
       SENS2 = SENS2 + 11*((Temp + 1500)**2)/2
    Temp = Temp - T2
    OFF = OFF - OFF2
    SENS = SENS - SENS2 
    Pres = (raw_d1*SENS/2097152 - OFF)/32768 # barometric pressure
    print ('Corrected Temperature', '%.1f' % Temp)
    print ('Corrected Pressure', '%.1f ' % Pres)
    ##for debugging purposes
    xbee.transmit(xbee.ADDR_BROADCAST, 'T=%.1f,P=%.1f' % (Temp, Pres))
    ##
    time.sleep(1.0)
    return Pres

##work on this GetCommand. needs to handle steady interval of pressure
##measurements while recieving xbee packets at irregular intervals
##xbee needs to use "data reception callback" rather than polling?
def GetCommand():
    # packet = None  # Set packet to none
    # while packet is None:   # While no packet has come in
    #     packet = xbee.receive()     # Try to receive packet
    # [xbee.receive() for i in range(100)]    # Clear the buffer
    # return packet.get('payload').decode('utf-8')[:3]    # Return the last three charters decoded
  try:
     packet = xbee.receive()
     [xbee.receive() for i in range(100)]
     reply = packet.get('payload').decode('utf-8')[:3]
     if reply is not None:
        print("Command:"+reply)
     return reply
  except:
     reply = ''
     return reply


def ProcessCommand(Command):
    print(Command)
    if Command == 'JKL':    #if command is Valve Open command
        Valve_Open()
    elif Command == 'MNO':  #if command is Valve Close command
        Valve_Close()
    elif Command == 'ABC':  #idle
        idle()
    elif Command =='VWX':
        Auto_Valve_On()
    elif Command =='PQR':
        Auto_Valve_Off()

def TransmitCommand(Command):
    print(Command)
    try:
      xbee.transmit(xbee.ADDR_BROADCAST, Command)
      print("Transmitted: " + Command)
    except:
      print("No Endpoint")

# idle
def idle():
    asc_led.value(0)
    msp_pin.value(0)

def Valve_Open():
    msp_pin.value(1)
    Blink(asc_led)

def Valve_Close():
    msp_pin.value(0)
    Blink(asc_led)

def Auto_Valve_On():
    global autovalve
    autovalve = 1
    Blink(asc_led)

def Auto_Valve_Off():
    global autovalve
    autovalve = 0
    Blink(asc_led)

def Blink(pin):
    for i in range(5):
        pin.value(1)    #Pin High
        time.sleep_ms(50)   #Do nothing for 1 second
        pin.value(0)    #Pin Low
        time.sleep_ms(50)   #Do nothing for 1 second


#Main Loop
def main():
    print ('i2c scan addresses found: ',scan_I2C())
    print ('perform reset on pressure sensor, code = ',reset_ps())
    time.sleep(1) # short delay during conversion
    # read press sensor calibration PROM
    sensor_addr = addresses[0]
    global C1, C2, C3, C4, C5, C6
    C1 = read_c1()
    C2 = read_c2()
    C3 = read_c3()
    C4 = read_c4()
    C5 = read_c5()
    C6 = read_c6()


    print ('PROM C1 = ', C1)
    print ('PROM C2 = ', C2)
    print ('PROM C3 = ', C3)
    print ('PROM C4 = ', C4)
    print ('PROM C5 = ', C5)
    print ('PROM C6 = ', C6)

    while(1):
        

        Pres = GetPressure()
        if autovalve:
          if Pres < VClevel:
            TransmitCommand('MNO')
          elif Pres < VOlevel & Pres > VClevel:
            TransmitCommand('JKL')
          
            
        ##need to add timeout after valve_open sent
        time.sleep(3) #need to pause to sync clock, otherwise transmit will be messed up
        ProcessCommand(GetCommand())
        
        if Pin.value(Hall_pin)==1:
            Hall_effect="VCR"
            # Hall_effect = str(Pin.value(Hall_pin))  # converts pin value of Hall_pin to a String to use the transmit function later
        else:
            Hall_effect="VOA"
        try:
            xbee.transmit(xbee.ADDR_COORDINATOR, Hall_effect)

        except:
            pass
#-----------------------------------------------------------
main()

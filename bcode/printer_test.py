import serial
import time

# INSTALL FTDI VCP DRIVER BEFOREHAND
ser = serial.Serial('COM3', 250000, timeout=1)

time.sleep(2)

def pause():
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(line)
            if line.lower() == 'ok':
                break

def send(gcode):
    cmd = gcode+'\n'
    ser.write(cmd.encode())
    pause()

send('G28')
send('G91')
send('G1 X30')
time.sleep(3)
for i in range(20):
    send('M42 P8 S128')
    time.sleep(0.2)
    send('M42 P8 S0')
    time.sleep(0.2)
    send('G1 Y10 F3000')

ser.close()

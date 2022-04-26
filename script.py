#!/usr/bin/python3
import sys, math, operator, json, time, board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


lugar = "UCC Av. 39"
lat = "4.6269525"
lon = "-74.0688642"

t = 19  # temperatura en centigrados
h = 63  # humedad

#
# Parametros del sensor - constantes
#
# The load resistance on the board
RLOAD = 10.0
# Calibration resistance at atmospheric CO2 level
RZERO = 76.63
# Parameters for calculating ppm of CO2 from sensor resistance
PARA = 116.6020682
PARB = 2.769034857

# Parameters to model temperature and humidity dependence
CORA = 0.00035
CORB = 0.02718
CORC = 1.39538
CORD = 0.0018
CORE = -0.003333333
CORF = -0.001923077
CORG = 1.130128205

# Atmospheric CO2 level for calibration purposes
ATMOCO2 = 412.5


def getCorrectionFactor(t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG):
    # Linearization of the temperature dependency curve under and above 20 degree C
    # below 20degC: fact = a * t * t - b * t - (h - 33) * d
    # above 20degC: fact = a * t + b * h + c
    # this assumes a linear dependency on humidity
    if t < 20:
        return CORA * t * t - CORB * t + CORC - (h-33.)*CORD
    else:
        return CORE * t + CORF * h + CORG


def getResistance(value_pin, RLOAD):
    return ((1023./value_pin) - 1.)*RLOAD


def getCorrectedResistance(t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG, value_pin, RLOAD):
    return getResistance(value_pin, RLOAD) / getCorrectionFactor(t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG)


def getPPM(PARA, RZERO, PARB, value_pin, RLOAD):
    return PARA * math.pow((getResistance(value_pin, RLOAD)/RZERO), -PARB)


def getCorrectedPPM(t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG, value_pin, RLOAD, PARA, RZERO, PARB):
    return PARA * math.pow((getCorrectedResistance(t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG, value_pin, RLOAD)/RZERO), -PARB)


def getRZero(value_pin, RLOAD, ATMOCO2, PARA, PARB):
    return getResistance(value_pin, RLOAD) * math.pow((ATMOCO2/PARA), (1./PARB))


def getCorrectedRZero(t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG, value_pin, RLOAD, ATMOCO2, PARA, PARB):
    return getCorrectedResistance(t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG, value_pin, RLOAD) * math.pow((ATMOCO2/PARA), (1./PARB))


def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


if __name__ == "__main__":
    print("\nIniciando ciclo MQ135...")

    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the ADC object using the I2C bus
    ads = ADS.ADS1115(i2c)

    # Create single-ended input on channel 0
    chan = AnalogIn(ads, ADS.P0)

    while True:

        value_ads = chan.value  # value obtained by ADS1115
        value_pin = map((value_ads - 565), 0, 26690,
                        0, 1023)  # 565 / 535 fix value
        rzero = getRZero(value_pin, RLOAD, ATMOCO2, PARA, PARB)
        correctedRZero = getCorrectedRZero(
            t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG, value_pin, RLOAD, ATMOCO2, PARA, PARB)
        resistance = getResistance(value_pin, RLOAD)
        ppm = getPPM(PARA, RZERO, PARB, value_pin, RLOAD)
        correctedPPM = getCorrectedPPM(
            t, h, CORA, CORB, CORC, CORD, CORE, CORF, CORG, value_pin, RLOAD, PARA, RZERO, PARB)
        print("\t chan.value: %s" % str(chan.value))
        print("\t MQ135 RZero: %s" % round(rzero))
        print("\t Corrected RZero: %s" % round(correctedRZero))
        print("\t Resistance: %s" % round(resistance))
        print("\t PPM: %s" % round(ppm))
        print("\t Corrected PPM: %s ppm" % round(correctedPPM))

        # Guardo datos en csv
        f = open("datos.csv", "a")
        f.write(time.strftime('%Y-%m-%d %H:%M:%S'))
        f.write(";")
        f.write(str(round(correctedPPM)))
        f.write("\n")
        f.close()

        print("-------------")
        time.sleep(60)

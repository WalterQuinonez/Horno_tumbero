# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 14:47:11 2025

@author: LAL

Pide data de la temperatura a arduino y grafica de manera continua. A diferencia de las pruebas anteriores, en las que arduino 
estaba continuamente midiendo, ahora pido que la medicion se realice y se transmita a la PC cuando lo necesito (defino un comando GET). 
Esto arregla dos problemas, por un lado el tema de ejecuciones sucesivas y por otro lado el problema que surge de sincronizacion cuando python 
sigue midiendo y la PC esta interactuanco con la fuente. 
La cantidad de puntos que se muestran en pantalla de manera simultanea se puede cambiar. Cuando se supera este numero, 
las mediciones mas antiguas se pierden y se agregan las nuevas. Esto se hace con deques. 
"""


import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import sys
from collections import deque
import time
import serial
import numpy as np


def medicion_temp_arduino(ser): 
    t0 = time.time()
    try:
        ser.write(b'GET\n')  # Pido una nueva medición
        linea = ser.readline().decode().strip()
        dt = time.time() - t0
        if linea:
            try:
                temper = float(linea)
                return temper
            except ValueError:
                print(f'Dato inválido: {linea}')
                return None
        return None
    except Exception as e:
        print(f"Error leyendo temperatura: {e}")
        return None



'''conecto arduino'''
arduino = serial.Serial('COM3', 9600, timeout=1)
print('Esperando conexion con Arduino')
time.sleep(2)  # dejar que Arduino reinicie


''' Configuración general del grafico '''
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Gráfico en tiempo real")
win.resize(800, 500)
plot = win.addPlot(title="Temperatura en tiempo real")
plot.setLabel('left', 'Temperatura', '°C')
plot.setLabel('bottom', 'Tiempo', 's')
plot.showGrid(x=True, y=True)
# Línea de datos
curve = plot.plot(pen='y')
# Buffer de datos
max_points = 1200  # número de puntos visibles
x = deque(maxlen=max_points)
y = deque(maxlen=max_points)




'''Empiezo a graficar y guardar data de tension, corriente, etc. '''
# Guardar tiempo inicial
start_time = time.time()

# Temporizador de actualización
def update():
    t = time.time() - start_time  # tiempo relativo desde t = 0
    temp  = medicion_temp_arduino(arduino)
    if temp is not None:
        x.append(t)
        y.append(temp)
        curve.setData(list(x), list(y))


timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(500)  # Actualización cada 100 ms

# Ejecutar aplicación
if __name__ == '__main__':
    QtWidgets.QApplication.instance().exec()

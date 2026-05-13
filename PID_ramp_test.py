# -*- coding: utf-8 -*-
"""
Created on Tue Jun 24 15:30:33 2025

@author: Walter Quiñonez
"""

'''
Prueba para determinar los parametros del control PID. La idea es ver la respuesta 
del sistema a un escalon y usar el metodo de Ziegler–Nichols. Para esto tengo que medir 
durante el tiempo necesario para que la temperatura aumente hasta llegar a un valor constate 
y mas o menos estable (quiero ver mas alla del transitorio). 

Grafico en tiempo real la temperatura vs tiempo y la corriente aplicada vs tiempo. 
Cuando termina la medicion se guarda toda la data. Por ahora lo hago en un archivo .npy


'''
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import sys
from collections import deque
import time
import serial
import numpy as np
from simple_pid import PID


def enviar_comando_fuente(ser, comando):
    '''Cada comando que mando a la fuente tarda 1.1 segundos en procesarse'''
    comando_full = comando + '\r\n' # Algunos dispositivos requieren fin de línea CR+LF
    ser.write(comando_full.encode('utf-8')) # Enviar comando
    time.sleep(0.1) # Esperar respuesta
    respuesta = ser.readline().decode('utf-8').strip()
    return respuesta

def reset_fuente(fuente): 
    '''Seteo el voltaje en cero, apago la salida y habilito los controles del panel frontal'''
    enviar_comando_fuente(fuente ,'PV 0') #seteo voltaje en cero
    enviar_comando_fuente(fuente ,'OUT 0') #apaga la salida
    enviar_comando_fuente(fuente ,'RMT 0') #habilito los controles panel frontal
    return


def medicion_temp_arduino(ser): 
    '''La medicion de temperatura se hace a demanda, el arduino no esta midiendo hasta
    que se envia este comando. Los valores no numericos como inf, nan y cosas del estilo 
    dan un error pero no devuelven nada. De esta forma, las funciones que plotean solo lo hacen si arduino 
    valores que tienen sentido.'''
    try:
        ser.write(b'GET\n')  # Pido una nueva medición
        linea = ser.readline().decode().strip()
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


def data_fuente(s):
    '''Le da formato a la data que viene de la fuente para poder plotear y guardar'''
    Vmedido , Vset, Imedido, Iset, OVP, UVP = map(float, s.split(','))
    resultado = f"Vmedido = {Vmedido}, Vset = {Vset}, Imedido = {Imedido}, Iset = {Iset}"
    print(resultado)
    return Vmedido , Vset, Imedido, Iset

def guardar_data_txt(data, nombre_archivo_data):   
    nombres = ['tiempo(s)', 'Voltaje medido (V)','Voltaje set (V)',
               'Corriente medida (A)','Corriente set (A)', 'Temperatura (°C)']
    nombre_data = nombre_archivo_data + '.txt' 
    np.savetxt(nombre_data ,  data, fmt = '%.5f',delimiter= '\t', 
               header = '\t'.join(nombres) , comments= '')
    return print (f'Data guardada en textfile {nombre_data}')
    
##################################################################################################
##################################################################################################


'''Conecto la fuente'''
puerto_fuente = 'COM6' # Cambia &#39;COM3&#39; por el puerto serial que uses (ej.&#39;/dev/ttyUSB0&#39; en Linux)
baudrate = 9600
fuente = serial.Serial(puerto_fuente, baudrate, timeout=1)
time.sleep(2)  


TEMP_INITIAL = 350.0               # Starting temperature (room temp, estimate)
TEMP_TARGET = 500.0               # Final temperature in °C
RAMP_RATE = 20.0                 # °C per minute
RAMP_RATE_PER_SEC = RAMP_RATE / 60.0  # °C per second
VOLTAGE_MIN = 0.0                 # Minimum voltage
VOLTAGE_MAX = 12.0                # Maximum voltage (adjust to your PSU)

corriente_maxima = 21.5 # En amperes
max_points = 1200  # número de puntos visibles
duration = 60*90  # segundos 
nombre_archivo_data = 'datos_temperatura_12v_21.5A'
tasa_refresco_plot = 100    # Actualización cada 100 ms


# --- PID Setup ---
pid = PID(Kp=3.783, Ki=0.0946, Kd=37.83, setpoint=TEMP_INITIAL)
pid.output_limits = (VOLTAGE_MIN, VOLTAGE_MAX)

'''seteo fuente'''
print('addres ' +  f'{enviar_comando_fuente(fuente ,'ADR 6')}')
print('IDN ' + f'{enviar_comando_fuente(fuente ,'IDN?')}')
print('Clear ' +f'{ enviar_comando_fuente(fuente ,'CLS')}' )
print(f'corriente maxima {corriente_maxima}A ' + f'{enviar_comando_fuente(fuente ,f'PC {corriente_maxima}')}' ) # con esto fijo la corriente de salida maxima

'''conecto arduino'''
arduino = serial.Serial('COM5', 9600, timeout=1)
print('Esperando conexion con Arduino')
time.sleep(2)  # dejar que Arduino reinicie

##################################################################################################
##################################################################################################
''' Configuración general del grafico '''
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Gráfico en tiempo real")
win.resize(1000, 600)

# --- Primer gráfico: Temperatura ---
plot = win.addPlot(title="Temperatura en tiempo real")
plot.setLabel('left', 'Temperatura', '°C')
plot.setLabel('bottom', 'Tiempo', 's')
plot.showGrid(x=True, y=True)
curve_temp = plot.plot(pen='y')

# --- Segundo gráfico: Corriente ---
win.nextRow()
plot_corr = win.addPlot(title="Corriente en tiempo real")
plot_corr.setLabel('left', 'Corriente', 'A')
plot_corr.setLabel('bottom', 'Tiempo', 's')
plot_corr.showGrid(x=True, y=True)
curve_corr = plot_corr.plot(pen='c')  # cyan

# Buffer de datos para plot
x = deque(maxlen=max_points)
y_temp = deque(maxlen=max_points)
y_corr = deque(maxlen=max_points)

#aca guardo la data
Vm = []
Vs= []
Im= []
Is = []
temp_medida = []
tiempo = []
##################################################################################################
##################################################################################################
'''Seteo la fuente para que mande la tension fija'''
print('Controles panel frontal bloqueados ' + f'{enviar_comando_fuente(fuente ,'RMT 2')}' )
print('Salida prendida ' + f'{enviar_comando_fuente(fuente ,'OUT 1')}') #prende y apaga la salida
print('Espero 2 segundos')
time.sleep(2)
print('mando pulso')

##################################################################################################
##################################################################################################
'''Empiezo a graficar y guardar data de tension, corriente, etc. '''
# Guardar tiempo inicial
start_time = time.time()

# Temporizador de actualización
def update():
    try:
        t = time.time() - start_time  # tiempo relativo desde t = 0
        if t > duration: 
            #Cierro conexion con arduino, reseteo la fuente y guardo la data
            print("Tiempo completado. Cerrando aplicación.")
            timer.stop()
            reset_fuente(fuente)
            arduino.close()
            data = np.array([tiempo ,Vm, Vs, Im, Is, temp_medida]).T  # Transponer para que cada lista sea una columna
            np.save(nombre_archivo_data, data)
            print(f"Datos guardados en {nombre_archivo_data}.npy'")
            guardar_data_txt(data, nombre_archivo_data)
            return   
        
        temp  = medicion_temp_arduino(arduino)
        setpoint = min(TEMP_INITIAL + t * RAMP_RATE_PER_SEC, TEMP_TARGET)
        pid.setpoint = setpoint
        # PID control
        voltage = pid(temp)
        enviar_comando_fuente(fuente ,f'PV {voltage}') # +1.1 seg
    
        if  temp is not None:
            estado_fuente = enviar_comando_fuente(fuente ,'DVC?') # +1.1 seg
            Vmedido , Vset, Imedido, Iset = data_fuente(estado_fuente) #esto devuelve corriente y voltaje medido como float
            Vm.append(Vmedido)
            Vs.append(Vset)
            Im.append(Imedido)
            Is.append(Iset)
            temp_medida.append(temp)
            tiempo.append(t)
            
            x.append(t)
            y_temp.append(temp)
            y_corr.append(Imedido)
            curve_temp.setData(list(x), list(y_temp))
            curve_corr.setData(list(x), list(y_corr))

    except KeyboardInterrupt:
        print('Interrupido por usuario.')
        timer.stop()
        reset_fuente(fuente)
        arduino.close()
        fuente.close()
        data = np.array([tiempo ,Vm, Vs, Im, Is, temp_medida]).T  # Transponer para que cada lista sea una columna
        np.save(nombre_archivo_data, data)
        print(f"Datos guardados en {nombre_archivo_data}.npy'")
        guardar_data_txt(data, nombre_archivo_data)
    
        
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(tasa_refresco_plot)  # Actualización cada 100 ms

# Ejecutar aplicación
if __name__ == '__main__':
    QtWidgets.QApplication.instance().exec()
    
    

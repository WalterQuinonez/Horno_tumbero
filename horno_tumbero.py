# -*- coding: utf-8 -*-
"""
Created on Tue Dec  9 11:36:38 2025

@author: walte
"""

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QFont  
import sys
import os
import time
import pyqtgraph as pg
from collections import deque
from simple_pid import PID
from EquiposLAL import ArduinoUNO, TDKLambdaGENH20


class ControlTemperatura(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Cargar GUI
        ruta_ui = os.path.join(os.path.dirname(__file__), "control_temperatura6.ui")
        uic.loadUi(ruta_ui, self)

        #Redirecciono las salidas de la consola al panel de la GUI
        self.consola = EmisorConsola()
        self.consola.texto.connect(self.mostrar_log)
        self._stdout_original = sys.stdout
        self._stderr_original = sys.stderr
        sys.stdout = self.consola
        sys.stderr = self.consola
        
        # Botones
        self.boton_on_off.clicked.connect(self.toggle_medicion)
        self.boton_actualizar.clicked.connect(self.actualizar_parametros_pid)
        self.boton_enfriar.clicked.connect(self.activar_enfriamiento)
        self.medicion_activa = False
        self.boton_on_off.setText("ON")
        self.boton_on_off.setStyleSheet("background-color: lightgreen; color: black;")

        # Estilo display temperatura
        self.label_temp_actual.setStyleSheet("""
        background-color: #1b3b1b;
        color: white;
        font-size: 28pt;
        font-weight: bold;
        border: 2px solid black;
        border-radius: 8px;
        padding: 6px;
        qproperty-alignment: 'AlignCenter';
        """)

        # Configurar gráficos
        self.configurar_graficos(self.Grafico_temperatura, xlabel='Tiempo [s]', ylabel='Temperatura [°C]')
        self.configurar_graficos(self.Grafico_corriente, xlabel='Tiempo [s]', ylabel='Corriente [A]')

        # Buffers de datos
        self.max_puntos = 4000
        self.tiempo_temp = deque(maxlen=self.max_puntos)
        self.temperatura_plot = deque(maxlen=self.max_puntos)
        self.tiempo_corr = deque(maxlen=self.max_puntos)
        self.corriente_plot = deque(maxlen=self.max_puntos)

        self.curva_temp = self.Grafico_temperatura.plot(pen=pg.mkPen('r', width=2))
        self.curva_corr = self.Grafico_corriente.plot(pen=pg.mkPen('b', width=2))

        # Timer gráficos
        self.timer_plot = QtCore.QTimer()
        self.timer_plot.timeout.connect(self.actualizar_graficos)
        self.timer_plot.start(200)

        # Archivo de datos
        self.archivo_datos = None

        # Worker (será único)
        self.worker = None

    def configurar_graficos(self, grafico, xlabel='', ylabel='', title=''):
        grafico.setBackground('w')
        grafico.showGrid(x=True, y=True, alpha=0.3)
        grafico.setLabel('left', ylabel, **{'color': 'black', 'font-size': '14pt'})
        grafico.setLabel('bottom', xlabel, **{'color': 'black', 'font-size': '14pt'})
        grafico.setTitle(title, color='black', size='14pt')

        font = QFont('Arial', 12)
        grafico.getAxis('left').setStyle(tickFont=font)
        grafico.getAxis('bottom').setStyle(tickFont=font)

    def toggle_medicion(self):
        if not self.medicion_activa:
            valido, mensaje = self.verificar_campos()
            if not valido:
                QMessageBox.critical(self, "Error de entrada", mensaje)
                return

            self.medicion_activa = True
            self.boton_on_off.setText("OFF")
            self.boton_on_off.setStyleSheet("background-color: red; color: white;")
            self.iniciar_medicion()
        else:
            self.medicion_activa = False
            self.boton_on_off.setText("ON")
            self.boton_on_off.setStyleSheet("background-color: lightgreen; color: black;")
            self.detener_medicion()


    def verificar_campos(self):
        try:
            self.rate_float = float(self.lineEdit_rate.text().strip())
            self.setpoint_float = float(self.lineEdit_setpoint.text().strip())
        except ValueError:
            return False, "Solo valores numéricos."

        if not (1 <= self.rate_float <= 20):
            return False, "Rate debe estar entre 1 y 20."
        if not (30 <= self.setpoint_float <= 900):
            return False, "Setpoint debe estar entre 30 y 850."

        return True, ""

    def iniciar_medicion(self):

        # Limpiar buffers
        self.tiempo_temp.clear()
        self.temperatura_plot.clear()
        self.tiempo_corr.clear()
        self.corriente_plot.clear()

        # Crear archivo
        self.nombre_archivo = f"medicion_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        self.archivo_datos = open(self.nombre_archivo, "w", encoding="utf-8")
        self.archivo_datos.write("t[s]\ttemp[°C]\tcorr[A]\tvolt[V]\tsetpoint[°C]\n")

        # Crear worker unificado
        self.worker = WorkerControl()
        self.worker.configurar_PID(self.setpoint_float,
                                   self.rate_float)

        # Conectar señales
        self.worker.datos_signal.connect(self.recibir_datos)
        self.worker.estado_signal.connect(self.mostrar_alerta)

        self.worker.start()

    def recibir_datos(self, datos):
        t = datos['t']
        temp = datos['temp']
        corr = datos['corr']
        volt = datos['volt']
        sp = datos['sp']

        # Actualizar display
        self.label_temp_actual.setText(f"{temp:.2f} °C")

        # Guardar para gráficas
        self.tiempo_temp.append(t)
        self.temperatura_plot.append(temp)
        self.tiempo_corr.append(t)
        self.corriente_plot.append(corr)

        # Guardar archivo
        try:
            if self.archivo_datos and not self.archivo_datos.closed:
                self.archivo_datos.write(f"{t:.3f}\t{temp:.3f}\t{corr:.6f}\t{volt:.3f}\t{sp:.3f}\n")
        except:
            pass

    def actualizar_parametros_pid(self):

        if not self.medicion_activa or self.worker is None:
            return

        try:
            rate = float(self.lineEdit_rate.text())
            sp = float(self.lineEdit_setpoint.text())
        except ValueError:
            return

        self.worker.actualizar_pid_signal.emit(sp, rate)
   
    def activar_enfriamiento(self):
        if self.worker:
            self.worker.set_modo_enfriar(True)
            print("Enfriando")

    def mostrar_alerta(self, msg):
        print(msg)

    def mostrar_log(self, msg):
        self.LogConsole.appendPlainText(msg)

    def actualizar_graficos(self):
        if len(self.tiempo_temp) > 0:
            self.curva_temp.setData(list(self.tiempo_temp), list(self.temperatura_plot))
        if len(self.tiempo_corr) > 0:
            self.curva_corr.setData(list(self.tiempo_corr), list(self.corriente_plot))

    def detener_medicion(self):
        if self.worker:
            self.worker.detener()
            self.worker.wait()
            self.worker = None

        if self.archivo_datos and not self.archivo_datos.closed:
            self.archivo_datos.close()
            print(f"✅ Archivo cerrado: {self.nombre_archivo}")

    def closeEvent(self, event):
        sys.stdout = self._stdout_original
        sys.stderr = self._stderr_original
        self.detener_medicion()
        event.accept()


# ===================================================================
# Worker Unificado
# ===================================================================

class WorkerControl(QtCore.QThread):
    datos_signal = QtCore.pyqtSignal(object)
    estado_signal = QtCore.pyqtSignal(str)
    actualizar_pid_signal = QtCore.pyqtSignal(float, float)

    def __init__(self, pid_params=None):
        super().__init__()

        self._detener = False
        self.actualizar_pid_signal.connect(self.actualizar_PID_en_vivo)
        self.modo_enfriar = False

        # PID
        if pid_params is None:
            pid_params = dict(Kp=1.5, Ki=0.1, Kd=5.0)
        self.pid = PID(**pid_params)
        self.pid.output_limits = (0, 14)

        self.setpoint_inicial = 0
        self.setpoint_final = 0
        self.rate = 1
        self.t0 = None
        self.t_rampa0 = None
        self.temp_actual = None

    def medir_temperatura_inicial(self, n=10, offset=10.0):
        temps = []
        for i in range(n):
            temp = self.arduino.medicion_temp_arduino(self.arduino_ser)
            if temp is not None:
                temps.append(temp)
            self.msleep(200)

        if len(temps) == 0:
            raise RuntimeError("No se pudo medir la temperatura inicial")

        T_prom = sum(temps) / len(temps)
        T_ini = T_prom + offset

        self.estado_signal.emit(
            f"T inicial automática: {T_prom:.2f} °C → {T_ini:.2f} °C"
        )

        return T_ini


    def configurar_PID(self,  T_final, rate):
        self.setpoint_final = T_final
        self.rate = rate

    def actualizar_PID_en_vivo(self, nuevo_setpoint, nuevo_rate):
        if self.temp_actual is None:
            return

        self.setpoint_inicial = self.pid.setpoint
        self.setpoint_final = nuevo_setpoint
        self.rate = nuevo_rate
        self.t_rampa0 = time.time()  # SOLO reinicia la rampa

        self.pid.reset()  # Esto es de SimplePID y borra los terminos acumlados integrales y derivativo 

        self.estado_signal.emit(
            f"PID actualizado | SP={nuevo_setpoint:.1f} °C | rate={nuevo_rate:.2f} °C/min"
        )

    def set_modo_enfriar(self, estado):
        self.modo_enfriar = estado

    def detener(self):
        self._detener = True

    def iniciar_conexiones(self):
        # Conectar primero fuente
        self.estado_signal.emit("Conectando fuente...")
        self.fuente  = TDKLambdaGENH20()
        #detecto en que COM# esta arduino}
        self.port_fuente = self.fuente.detectar_fuente_por_vidpid()
        if self.port_fuente is None:
            raise RuntimeError("No se encontró fuente")
        # AHORA abro el puertp
        self.fuente_ser = self.fuente.conectar_fuente(self.port_fuente)
        self.estado_signal.emit(f"Fuente lista en {self.port_fuente}.")

        # Luego Arduino
        self.estado_signal.emit("Conectando Arduino...")
        self.arduino = ArduinoUNO()
        #detecto en que COM# esta arduino
        self.port_arduino = self.arduino.detectar_arduino_por_vidpid()
        if self.port_arduino is None:
            raise RuntimeError("No se encontró Arduino")
        # AHORA abro el puertp
        self.arduino_ser = self.arduino.conectar_arduino(self.port_arduino)
        self.estado_signal.emit(f"Arduino listo en {self.port_arduino}.")

    def run(self):
        try:
            self.iniciar_conexiones()
        except Exception as e:
            self.estado_signal.emit(f"Error inicial: {e}")
            return

        self.t0 = time.time()
        self.t_rampa0 = self.t0

        # Medición automática de temperatura inicial
        self.setpoint_inicial = self.medir_temperatura_inicial(
            n=10,
            offset=5.0
        )

        self.pid.setpoint = self.setpoint_inicial


        while not self._detener:

            t_global = time.time() - self.t0
            t_rampa = time.time() - self.t_rampa0

            delta = self.rate / 60 * t_rampa

            if self.setpoint_final >= self.setpoint_inicial:
                # rampa ascendente
                sp = min(self.setpoint_inicial + delta, self.setpoint_final)
            else:
                # rampa descendente
                sp = max(self.setpoint_inicial - delta, self.setpoint_final)

            
            self.pid.setpoint = sp

            # Medición temperatura
            temp = self.arduino.medicion_temp_arduino(self.arduino_ser)

            if temp == "FALLO":
                self.estado_signal.emit("Arduino en fallo crítico. Proceso detenido.")
                break

            if temp is None:
                continue
            
            self.temp_actual = temp
            
            
            # PID -> Voltaje
            if self.modo_enfriar:
                volt = 0.0
                self.arduino_ser.write(b"AbrirRele\n")

            else:
                volt = self.pid(temp)

            self.fuente.aplicar_voltaje(volt)

            # Leer corriente solo después
            corr = self.fuente.leer_corriente()

            # Emitir datos ordenados
            self.datos_signal.emit({
                't': t_global,
                'temp': temp,
                'corr': corr,
                'volt': volt,
                'sp': sp
            })

            self.msleep(200)

        # Cierre ordenado
        try:
            self.fuente.reset_fuente()
            self.fuente.close()
        except:
            pass

        try:
            self.arduino.close()
        except:
            pass

        self.estado_signal.emit("Worker finalizado.")

class EmisorConsola(QtCore.QObject):
    texto = QtCore.pyqtSignal(str)

    def write(self, msg):
        if msg.strip():
            self.texto.emit(msg)

    def flush(self):
        pass



# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ControlTemperatura()
    window.show()
    sys.exit(app.exec_())

import time
import serial
import os
from PyQt5 import uic
import random 
import pyqtgraph as pg
from PyQt5.QtWidgets import QMainWindow,  QMessageBox
from PyQt5.QtCore import QTimer
import serial.tools.list_ports


class MainWindow(QMainWindow):
    """Clase base para generar ventanas de interfaces (GUI). Llama a la plantilla .ui (puede estar armada
    en QTdesigner) y en este caso tiene 1 botón para inicia, 3 campos de texto para ingresar parametros y 
    dos graficos en función del tiempo. 

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'control_temperatura.ui'), self)

        # conectar el botón al método
        self.boton_on_off.clicked.connect(self.toggle_button)

        # estado inicial
        self.estado_on = True
        self.boton_on_off.setText("ON")
        self.boton_on_off.setStyleSheet("background-color: lightgreen; color: black;")

        # Gráficos
        self.configurar_graficos(self.Grafico_temperatura, xlabel='Tiempo[s]', ylabel='Temperatura [°C]')
        self.configurar_graficos(self.Grafico_corriente, xlabel='Tiempo[s]', ylabel='Corriente [A]')

        #Inicializar datos de temperatura
        self.tiempo = []
        self.temperaturas = []
        self.t_actual = 0
        self.temperatura_actual = 25.0

        # 🔹 Crear la curva en el gráfico de temperatura
        self.curva_temp = self.Grafico_temperatura.plot(pen=pg.mkPen('r', width=2))

        # 🔹 Timer para actualización
        # self.timer_temp = QTimer(self)
        # self.timer_temp.timeout.connect(self.actualizar_datos_temperatura)
        # self.timer_temp.start(1000)  # cada 1 segundo

        # 🔹 Label inicial
        self.label_temp_actual.setText(f"{self.temperatura_actual:.1f} °C")
        self.label_temp_actual.setText(f"{self.temperatura_actual:.1f} °C")
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



    def configurar_graficos(self, grafico, xlabel='', ylabel='', title=''):
        grafico.setBackground('w')
        grafico.showGrid(x=True, y=True, alpha=0.3)
        grafico.setLabel('left', ylabel, color='black', size='12pt')
        grafico.setLabel('bottom', xlabel, color='black', size='12pt')
        grafico.setTitle(title, color='w', size='14pt')

    def toggle_button(self):
        # Verificar que los campos sean numéricos y estén dentro de rango
        valido, mensaje_error = self.verificar_campos()
        if not valido:
            QMessageBox.critical(self, "Error de entrada", mensaje_error)
            return  # No cambia el botón si hay error

        # Si todo está bien, alternar ON/OFF
        if self.estado_on:
            self.boton_on_off.setText("OFF")
            self.boton_on_off.setStyleSheet("background-color: red; color: white;")
        else:
            self.boton_on_off.setText("ON")
            self.boton_on_off.setStyleSheet("background-color: lightgreen; color: black;")

        self.estado_on = not self.estado_on

        

    def verificar_campos(self):
        """
        Devuelve (True, "") si todos los campos son válidos.
        Si hay error, devuelve (False, mensaje_error).
        """
        try:
            rate = float(self.lineEdit_rate.text().strip())
            setpoint = float(self.lineEdit_setpoint.text().strip())
            t_inicial = float(self.lineEdit_T_inicial.text().strip())
        except ValueError:
            return False, "Solo se permiten valores numéricos en Rate, Setpoint y T inicial."

        # Validar rangos
        if not (1 <= rate <= 20):
            return False, "El valor de 'Rate' debe estar entre 1 y 20."
        if not (30 <= setpoint <= 850):
            return False, "El valor de 'Setpoint' debe estar entre 30 y 850."
        if not (50 <= t_inicial <= 120):
            return False, "El valor de 'T inicial' debe estar entre 50 y 120."

        return True, ""


    #def actualizar_datos_temperatura(self):
    #    """
    #    Actualiza la gráfica y el label con una nueva temperatura (simulada o real)
    #    """
    #    # Si el botón está en OFF, no actualizar
    #    if not self.estado_on:
    #        return

    #    # Simular aumento o fluctuación de temperatura (reemplazalo por lectura real)
    #    self.temperatura_actual += random.uniform(-0.5, 0.8)
    #    self.t_actual += 1

    #    # Guardar datos
    #    self.tiempo.append(self.t_actual)
    #    self.temperaturas.append(self.temperatura_actual)

    #    # Actualizar gráfico
    #    self.curva_temp.setData(self.tiempo, self.temperaturas)

    #    # Actualizar label
    #    self.label_temp_actual.setText(f"{self.temperatura_actual:.1f} °C")
 





class ArduinoUNO():
  
    # -------------------------------------------------------------------------

        
    def medicion_temp_arduino(self, ser):
        '''La medicion de temperatura se hace a demanda, el arduino no esta midiendo hasta
        que se envia este comando. Los valores no numericos como inf, nan y cosas del estilo 
        dan un error pero no devuelven nada. De esta forma, las funciones que plotean solo lo hacen si arduino 
        valores que tienen sentido.
        Devuelve:
            float -> temperatura válida
            None  -> dato inválido común
            "FALLO" -> fallo crítico del Arduino
        '''
        try:
            ser.write(b'GET\n')
            linea = ser.readline().decode().strip()

            if not linea:
                return None

            #FALLO CRÍTICO DEL ARDUINO
            if "ARDUINO FALLANDO" in linea:
                print("Arduino reportó fallo crítico")
                return "FALLO"

            try:
                temper = float(linea)
                return temper
            except ValueError:
                print(f'Dato inválido: {linea}')
                return None

        except Exception as e:
            print(f"Error leyendo temperatura: {e}")
            return None    
   
 
    # -------------------------------------------------------------------------
    def detectar_arduino_por_vidpid(self):
        
        ARDUINO_IDS = [
            ("2341", "0043"),  # Arduino UNO original
            ("1A86", "7523"),  # CH340 clones
            ("0403", "6001"),  # FTDI
        ]
    
        for port in serial.tools.list_ports.comports():
            vid_pid = port.hwid
            for vid, pid in ARDUINO_IDS:
                if f"VID:PID={vid}:{pid}" in vid_pid:
                    return port.device
        return None


    # -------------------------------------------------------------------------
    def reconectar_arduino(self, ser, max_intentos=4):
        print("Intentando reconectar Arduino...")
    
        # Cerrar puerto si está abierto
        try:
            ser.close()
            print("Puerto cerrado")
        except:
            print("Advertencia: el puerto ya estaba cerrado")
    
        time.sleep(5)
    
        nuevo_ser = None
    
        for intento in range(1, max_intentos + 1):
            print(f"Reintento {intento} de {max_intentos}")
    
            # Detecto si el Arduino aparece en el sistema
            port_arduino = self.detectar_arduino_por_vidpid()
    
            if port_arduino is None:
                print("Arduino no detectado en el sistema")
            else:
                print(f"Arduino encontrado en {port_arduino}, intentando conectar...")
    
                # Intento conectar
                try:
                    nuevo_ser = self.conectar_arduino(port_arduino)
                    if nuevo_ser is not None:
                        print("Reconexión exitosa")
                        return nuevo_ser
                except Exception as e:
                    print(f"Error conectando: {e}")
    
            # Espera antes del siguiente intento
            time.sleep(2)
    
        print("Se agotaron los intentos de reconexión del Arduino")
        return None   # o podés hacer:  raise Exception("No se pudo reconectar el Arduino")



    # -------------------------------------------------------------------------
    def conectar_arduino(self,port):
        '''Método para establecer conexion con arduino'''
        time.sleep(2)
        ser = serial.Serial(port, 9600, timeout=1)
        print('Esperando conexion con Arduino')
        time.sleep(2)  # dejar que Arduino reinicie
        print('Conectado con Arduino')
        return ser 





class TDKLambdaGENH20:
    """Control básico de la fuente TDK Lambda GENH20 mediante puerto serial."""

    def __init__(self):
        self.corriente_maxima = 22
        self.adr = 6
        self.fuente = None  # se inicializa vacía hasta conectar

    # -------------------------------------------------------------------------
    def enviar_comando_fuente(self, comando):
        """Envía un comando SCPI a la fuente y devuelve la respuesta."""
        if not hasattr(self, 'fuente') or self.fuente is None:
            raise Exception("No hay conexión activa con la fuente. Llame primero a conectar_fuente().")

        comando_full = comando + '\r\n'  # agrega retorno de carro y nueva línea
        self.fuente.write(comando_full.encode('utf-8'))
        time.sleep(0.1)  # la fuente tarda un poco en responder
        respuesta = self.fuente.readline().decode('utf-8').strip()
        return respuesta

    # -------------------------------------------------------------------------
    def detectar_fuente_por_vidpid(self):
        
        FUENTE_IDS = [ ("067B", "23A3")        ]
    
        for port in serial.tools.list_ports.comports():
            vid_pid = port.hwid
            for vid, pid in FUENTE_IDS:
                if f"VID:PID={vid}:{pid}" in vid_pid:
                    return port.device
        return None
    
    # -------------------------------------------------------------------------
    def conectar_fuente(self, port):
        """Abre la conexión serial con la fuente y realiza configuración inicial."""
        baudrate = 9600
        print('Esperando conexión con la fuente...')
        self.fuente = serial.Serial(port, baudrate, timeout=1)
        print('Conectado con fuente.')
        time.sleep(1)

        # Comunicación inicial y configuración
        print('Address: ' + self.enviar_comando_fuente(f'ADR {self.adr}'))
        print('Identificación: ' + self.enviar_comando_fuente('IDN?'))
        print('Clear: ' + self.enviar_comando_fuente('CLS'))
        print(f'Corriente máxima {self.corriente_maxima} A: ' +
              self.enviar_comando_fuente(f'PC {self.corriente_maxima}'))

        # Configuración remota y encendido
        print('Controles panel frontal bloqueados: ' + self.enviar_comando_fuente('RMT 2'))
        print('Salida prendida: ' + self.enviar_comando_fuente('OUT 1'))
        time.sleep(2)
        print('Conexión y configuración inicial completa.')

        return self.fuente

    # -------------------------------------------------------------------------
    def aplicar_voltaje(self, voltage):
        """Configura el voltaje de salida de la fuente según el valor calculado por el PID."""
        respuesta = self.enviar_comando_fuente(f'PV {voltage}')
        return respuesta
    
    
    # -------------------------------------------------------------------------    
    def leer_corriente(self):
        """Lee la corriente de salida real de la fuente."""
        respuesta = self.enviar_comando_fuente('MC?')
        try:
            return float(respuesta)
        except ValueError:
            print(f"Error leyendo corriente: {respuesta}")
            return None

    # -------------------------------------------------------------------------
    def reset_fuente(self):
        """Setea el voltaje en cero, apaga la salida y libera el panel."""
        if self.fuente and self.fuente.is_open:
            self.enviar_comando_fuente('PV 0')
            self.enviar_comando_fuente('OUT 0')
            self.enviar_comando_fuente('RMT 0')
            self.fuente.close()
            print("Fuente reseteada y conexión cerrada.")
        else:
            print("No hay una fuente conectada.")

    # -------------------------------------------------------------------------
    def data_fuente(self, s):
        """Formatea la respuesta de la fuente para su análisis o graficación."""
        Vmedido, Vset, Imedido, Iset, OVP, UVP = map(float, s.split(','))
        resultado = f"Vmedido={Vmedido} V, Vset={Vset} V, Imedido={Imedido} A, Iset={Iset} A"
        print(resultado)
        return Vmedido, Vset, Imedido, Iset

import time
import serial
import os
from PyQt5 import uic
import random 
import pyqtgraph as pg
from PyQt5.QtWidgets import QMainWindow,  QMessageBox
from PyQt5.QtCore import QTimer
import serial.tools.list_ports
import pyvisa 


###########################################################################################
###########################################################################################


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

        La comunicacion se hace con pyserial. 
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


###########################################################################################
###########################################################################################



class TDKLambdaGENH20:
    """Control básico de la fuente TDK Lambda GENH20 mediante puerto serial (pyserial)."""

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
    
    

###########################################################################################
###########################################################################################


class OWONodp3063:
    """Clase base para la fuente de tension/corriente OWON ODP3063. 
    La comunicacion se hace con pyvisa.

    14/1/2025: Como por ahora solo la voy a usar para implementar un heater, por defecto los 
    canales 1 y 2 van a estar conectados en serie y solo voy a hacer referencia al canal 1 
    cuando interactuo con la fuente.  
    
    """
    # -------------------------------------------------------------------------
    
    def __init__(self):
    
        self.fuente = None  # se inicializa vacía hasta conectar
        self.corriente_maxima = 5.8

    # -------------------------------------------------------------------------

    def detectar_fuente_por_vidpid(self, rm):
        """
        Detecta y abre la fuente OWON con USB VISA basado en el VID y PID de manera automatica.

        Parámetros:
            rm (obj) : Resource Manager global del programa. 

        Retorna:
            r (string): direccion del puerto en el que esta conectado la fuente

        Lanza:
            RuntimeError: si no se encuentra ningún dispositivo
        """
        vid = "0x5345"
        pid = "0x1235"
 
        # Buscar solo recursos USB
        recursos = rm.list_resources('?*USB?*')

        for r in recursos:
            partes = r.split("::")

            # Formato esperado: USB0::VID::PID::SERIAL::INTERFACE::INSTR
            if len(partes) >= 3:
                vid_r = partes[1]
                pid_r = partes[2]

                if vid_r.upper() == vid.upper() and pid_r.upper() == pid.upper():
                    print(f"Fuente encontrada: {r}")
                    return r

        raise RuntimeError(f"No se encontró ninguna fuente con VID={vid} y PID={pid}")


    # -------------------------------------------------------------------------


    def conectar_fuente_OWON_visa(self, rm ,port):
        """Conecta la fuente y hace la configuracion inicial para alimentar un heater. 
        14/1/2025: por default conecta en serie los canales 1 y 2, bloquea los controles del 
        aparato, setea las salidas a cero y activa la salida del canal 1 (en modo serie puedo 
        hacer referencia al canal 1 o 2).  

        Returns:
            fuente : objeto de la clase Resource de pyvisa
        """        
        
        self.fuente = rm.open_resource(port)  # Ajustar según tu equipo
        print('Identificación: ' + self.fuente.query("*IDN?"))
        # Configuración remota y encendido
        self.fuente.query('SYSTem:REMote') 
        print('Controles panel frontal bloqueados' )
        self.fuente.query('OUTP:SERies ON') 
        print('Canal 1 y 2 conectados en serie.' )
        self.fuente.write("APP:VOLT 0,0,0")
        
        print(f'Corriente maxima seteada : {self.corriente_maxima}.' )
        self.fuente.write("CURR " + f"{self.corriente_maxima}") 
        
        print('Voltajes de salida seteados a cero.' )
        self.fuente.write("CHAN:OUTP:ALL 1,0,0") 
        #PONER CORRIENTE DE SALIDA AL MAXIMO???
        print('Canal 1 activado.')
        time.sleep(2)
        print('Conexión y configuración inicial completa.')
        return self.fuente

    # -------------------------------------------------------------------------


    def set_voltaje(self, voltaje,canal):
        self.fuente.write("INST CH" + f"{canal}") 
        self.fuente.write("VOLT " + f"{float(voltaje)}") #setea el valor de voltaje para el canal elegido  
        return

    # -------------------------------------------------------------------------


    def set_corriente(self, corriente,canal):
        self.fuente.write("INST CH" + f"{canal}") 
        self.fuente.write("CURR " + f"{float(corriente)}") #setea el valor de voltaje para el canal elegido  
        return


    # -------------------------------------------------------------------------

    def leer_corriente(self):
        """Lee la corriente de salida real de la fuente."""
        respuesta = self.fuente.query("MEAS:CURR?")
        try:
            return float(respuesta)
        except ValueError:
            print(f"Error leyendo corriente: {respuesta}")
            return None


    # -------------------------------------------------------------------------

    def is_open(self, device):  
        try:
            device.write("*IDN?")
            abierto = True
            return abierto
        except pyvisa.errors.InvalidSession:
            abierto = False
            return abierto 
        

    
    def reset_fuente(self):
        """Setea el voltaje en cero, apaga la salida y libera el panel."""
        if self.fuente and self.is_open(self.fuente):
            self.fuente.write("APP:VOLT 0,0,0")
            self.fuente.write("CHAN:OUTP:ALL 0,0,0") 
            self.fuente.query('SYSTem:LOCal') 
            self.fuente.close()
            print("Fuente reseteada y conexión cerrada.")
        else:
            print("No hay una fuente conectada.")
    



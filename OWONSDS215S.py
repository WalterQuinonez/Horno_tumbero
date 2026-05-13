import numpy as np
import pyvisa as visa
import re
import json
import struct


class OWONSDS215S:
    def __init__(self):
        rm = visa.ResourceManager()
        try:
            self.osciloscopio = rm.open_resource('USB0::0x5345::0x1235::24400127::INSTR')
        except Exception as e:
            print(f'{e}')
    
    def configuracionInicial(self):
        pass

    def getDatosHeader(self):
        respuesta_json = self.osciloscopio.query(':DATA:WAVE:SCREen:HEAD?')
        inicio_json = respuesta_json.find('{')
        json_limpio_str = respuesta_json[inicio_json:]
        self.datosHeader = json.loads(json_limpio_str)
   
    def voltParams(self, canal):
        canal_info = next(channel for channel in self.datosHeader['CHANNEL'] if channel['NAME'] == canal)
        canal_escala_v_str = canal_info['SCALE']
        canal_offset_str = canal_info['OFFSET']

        canal_escala_volt = self._parseUnidades(canal_escala_v_str)
        canal_offset = float(canal_offset_str)
        return canal_offset, canal_escala_volt

    def timeParams(self):
        timeBase = self.datosHeader['TIMEBASE']
        timeBase_scale_str = timeBase['SCALE']
        segundos_por_division = self._parseUnidades(timeBase_scale_str)
        
        sample = self.datosHeader['SAMPLE']
        num_puntos = int(sample['DATALEN'])
        return num_puntos, segundos_por_division

    def _parseUnidades(self, info:str):
        unidades = {
        'V': 1, 'mV': 1e-3, 'uV': 1e-6, 
        's': 1, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9,
        'S':1, 'KS':1e3, 'MS':1e6, 'GS':1e9  
        }
        patron = re.compile(r"([\d\.\+\-Ee]+)\s*([a-zA-Z]+)") # Expresión regular para buscar "valor" y "unidad"
        match = patron.search(info) 

        if not match:
            valor = 0
            return valor
        valor = float(match.group(1))
        unidad = match.group(2)

        valor = valor*unidades[unidad]
        return valor

    def datosCrudos(self, canal):
        self.osciloscopio.write(f":DATA:WAVE:SCREen:{canal}?")
        raw_data = self.osciloscopio.read_raw()
        size = struct.unpack('<I', raw_data[:4])[0] # Primeros 4 bytes indican el tamaño
        data = raw_data[4:4+size]# Extraemos solo la parte de datos
        samples_u16 = np.frombuffer(data, dtype=np.uint16)# Cada punto = 2 bytes (12 bits útiles)

        samples_i16 = samples_u16.view(np.int16)  # misma memoria, interpretación signed
        samples_i16_12 = (samples_i16 & 0x0FFF)
        # convertir valores >2047 a negativos (dos's complement 12-bit)
        samples_i16_12 = np.where(samples_i16_12 > 2047, samples_i16_12 - 4096, samples_i16_12)
        return samples_i16_12

    def getData(self):
        self.osciloscopio.write(':RUNning STOP')
        
        self.getDatosHeader()
        
        ADC_pasos_por_division = 409.6
        
        volt1_crudo = self.datosCrudos('CH1')
        offset_div, escala_v = self.voltParams('CH1')
        # Conversión según manual OWON
        volt1 = (volt1_crudo/ADC_pasos_por_division)*escala_v - offset_div*escala_v/50
        
        self.osciloscopio.write(':RUNning RUN')

        divisiones_horizontales = 15 #Ver manual

        num_puntos, segundos_por_division = self.timeParams()

        duracion_total_segundos = divisiones_horizontales*segundos_por_division
        t_sample = duracion_total_segundos/num_puntos        

        tiempoSegundos = np.arange(int(num_puntos))*t_sample
        return tiempoSegundos, volt1


    def cierreFinal(self):
        pass
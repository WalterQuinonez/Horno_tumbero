import pyvisa
import time


def conectar_fuente_OWON_visa():
    puerto_fuente = 'USB0::0x5345::0x1235::23250450::0::INSTR'
    fuente = rm.open_resource(puerto_fuente)  # Ajustar según tu equipo
    print('Identificación: ' + fuente.query("*IDN?"))
    # Configuración remota y encendido
    fuente.query('SYSTem:REMote') 
    print('Controles panel frontal bloqueados' )
    fuente.baud_rate = 115200
    print('baud_rate: 115200' )
    fuente.write("APP:VOLT 0,0,0")
    print('Voltajes de salida seteados a cero.' )
    fuente.write("CHAN:OUTP:ALL 1,0,0") 
    #PONER CORRIENTE DE SALIDA AL MAXIMO???
    print('Canal 1 activado.')
    time.sleep(2)
    print('Conexión y configuración inicial completa.')
    return fuente

def set_voltaje(voltaje,canal):
    fuente.write("INST CH" + f"{canal}") 
    fuente.write("VOLT " + f"{float(voltaje)}") #setea el valor de voltaje para el canal elegido  
    return

def leer_corriente(device):
    """Lee la corriente de salida real de la fuente."""
    respuesta = device.query("MEAS:CURR?")
    try:
        return float(respuesta)
    except ValueError:
        print(f"Error leyendo corriente: {respuesta}")
        return None
    
def is_open(inst):  
    try:
        inst.write("*IDN?")
        abierto = True
        return abierto
    except pyvisa.errors.InvalidSession:
        abierto = False
        return abierto 
    
    
def reset_fuente():
    """Setea el voltaje en cero, apaga la salida y libera el panel."""
    if fuente and is_open(fuente):
        fuente.write("APP:VOLT 0,0,0")
        fuente.write("CHAN:OUTP:ALL 0,0,0") 
        fuente.query('SYSTem:LOCal') 
        fuente.close()
        print("Fuente reseteada y conexión cerrada.")
    else:
        print("No hay una fuente conectada.")




rm = pyvisa.ResourceManager()
fuente = conectar_fuente_OWON_visa()
set_voltaje(7, 1)
leer_corriente(fuente)
reset_fuente()

rm.close()









rm = pyvisa.ResourceManager()
print("Instrumentos encontrados:")
print(rm.list_resources())
fuente = rm.open_resource('USB0::0x5345::0x1235::23250450::0::INSTR')  # Ajustar según tu equipo



print(fuente.query("*IDN?"))
fuente.query("*IDN?")
fuente.query("VOLT?")
fuente.query("CURR?") 
fuente.write('OUTP:SERies ON')


fuente.write("CHAN:OUTP:ALL 0,0,0") 

fuente.write("INST CH1") 
fuente.write("VOLT 0.7") #setea el valor de voltaje para el canal elegido  
fuente.write("CURR 5.8")#setea el valor de corriente para el canal elegido   

fuente.write("CHAN:OUTP:ALL 1,0,0") #prende o apaga los canales
fuente.query("MEAS:VOLT?")
fuente.query("MEAS:CURR?")


fuente.write("APP:VOLT 5,0,0") # cambia el voltaje de los canales
fuente.query("VOLT?") #devuelve el valor seteado de voltaje
fuente.query("CURR?") #devuelve el valor seteado de corriente
fuente.write("CHAN:OUTP:ALL 0,0,0") 
fuente = rm.close_resource('USB0::0x5345::0x1235::23250450::0::INSTR')  # Ajustar según tu equipo


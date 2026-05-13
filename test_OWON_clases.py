# -*- coding: utf-8 -*-
"""
Created on Wed Jan 14 11:23:21 2026

@author: LAL
"""

import pyvisa
from EquiposLAL import OWONodp3063

rm = pyvisa.ResourceManager()

fuente  = OWONodp3063()
port = fuente.detectar_fuente_por_vidpid(rm)
fuente.conectar_fuente_OWON_visa(rm, port)
fuente.set_voltaje(2, 1)
fuente.set_corriente(3.8, 1)
fuente.reset_fuente()

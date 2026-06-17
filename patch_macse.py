#!/usr/bin/env python3
"""
patch_macsec.py — Patch para compilar o módulo macsec.ko
en Raspberry Pi OS (kernel 6.12.x) sen soporte hardware offload.

Problema: o kernel RPi elimina as estruturas macsec_ops en
phy_device e net_device, causando erros de compilación.
Solución: substituír as referencias problemáticas por NULL.

Funcións afectadas:
  - macsec_check_offload(): verifica se a NIC ten hardware MACsec
  - __macsec_get_ops(): devolve o punteiro ás ops hardware da NIC

Por que é seguro: a RPi 4B usa un Broadcom BCM54213 sen soporte
hardware MACsec. Estas funcións nunca se invocan en uso real.
O módulo resultante funciona en modo software puro (GCM-AES-128
via instrucións criptográficas ARMv8 do Cortex-A72).

Autor: Lucas González Torres
TFG — ESEI, Universidade de Vigo, Xuño 2026
Kernels probados: 6.12.75+rpt-rpi-v8
"""

with open('macsec.c', 'r') as f:
    content = f.read()

# Substitución 1: referencia a macsec_ops a través do PHY device
# real_dev -> phydev -> macsec_ops (chip de capa física do adaptador)
# Ao substituír por NULL: a función indica que non hai hardware offload
content = content.replace(
    "macsec->real_dev->phydev->macsec_ops",
    "NULL"
)

# Substitución 2: referencia a macsec_ops directamente en net_device
# Algúns adaptadores expoñen o offload a nivel de net_device
# Ao substituír por NULL: resolve tamén o erro
# "control reaches end of non-void function" en __macsec_get_ops()
content = content.replace(
    "macsec->real_dev->macsec_ops",
    "NULL"
)

with open('macsec.c', 'w') as f:
    f.write(content)

print("Patch aplicado correctamente en macsec.c")
print("Agora podes executar: make")

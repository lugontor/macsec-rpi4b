#!/usr/bin/env python3
"""
patch_macsec.py — Patch para compilar o módulo macsec.ko
en Raspberry Pi OS (kernel 6.12.x) sen soporte hardware offload.

Problema: o kernel RPi elimina as estruturas macsec_ops en
phy_device e net_device, causando erros de compilación.
Solución: substituír as referencias problemáticas por NULL.

Autor: Lucas González Torres — TFG ESEI, Universidade de Vigo, 2026
"""

with open("macsec.c", "r") as f:
    c = f.read()

c = c.replace("macsec->real_dev->phydev->macsec_ops", "NULL")
c = c.replace("macsec->real_dev->macsec_ops", "NULL")

with open("macsec.c", "w") as f:
    f.write(c)

print("Patch aplicado correctamente en macsec.c")

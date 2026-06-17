# Makefile para compilar macsec.ko como módulo externo
# en Raspberry Pi OS kernel 6.12.75+rpt-rpi-v8
#
# Uso:
#   make        — compila macsec.ko
#   make clean  — elimina os ficheiros de compilación
#
# Requisitos:
#   linux-headers-$(uname -r) instalados
#   patch_macsec.py aplicado previamente sobre macsec.c

obj-m += macsec.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean

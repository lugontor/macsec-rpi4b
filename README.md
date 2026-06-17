# MACsec en Raspberry Pi 4B — Patch Python e scripts de configuración

> **Traballo de Fin de Grao**
> *Entorno de Prototipado MACsec — Implementación e validación de IEEE 802.1AE sobre Raspberry Pi 4B*
> Lucas González Torres — ESEI, Universidade de Vigo — Xuño 2026

---

## 📋 Descrición

Este repositorio contén o **patch Python**, o **Makefile** e os **scripts de configuración** necesarios para compilar e despregar o módulo `macsec.ko` en kernels **Raspberry Pi OS** (rpi-6.12.y / rpi-6.18.y), que non inclúen este módulo de forma nativa nin as estruturas `macsec_ops` nos seus headers.

O contorno de prototipado consiste en dous nodos **Raspberry Pi 4B** que implementan MACsec (IEEE 802.1AE) con cifrado **GCM-AES-128** en modo software puro, verificado con Wireshark, tcpdump e iperf3.

---

## 🖥️ Hardware e software do contorno

| Compoñente | Nodo A | Nodo B |
|---|---|---|
| Hardware | Raspberry Pi 4B (2 GB) | Raspberry Pi 4B (2 GB) |
| Kernel final (con patch) | `6.12.75+rpt-rpi-v8` | `6.12.75+rpt-rpi-v8` |
| IP experimento | `10.0.0.1/24` (macsec0) | `10.0.0.2/24` (macsec0) |
| Cipher suite | GCM-AES-128 | GCM-AES-128 |
| Offload hardware | off (software puro) | off (software puro) |

---

## ⚠️ O problema: por que falla a compilación directa

O kernel de Raspberry Pi OS é un fork do kernel Linux upstream mantido por Raspberry Pi Foundation. A diferenza do kernel upstream, **os kernels RPi teñen eliminado o soporte de hardware offload MACsec**. Isto significa que as estruturas `phy_device` e `net_device` nos headers do kernel RPi **non inclúen o campo `macsec_ops`**, que no kernel upstream apunta ás operacións de cifrado hardware de NICs con soporte MACsec nativo.

### Erro exacto ao compilar (idéntico en kernel 6.18 e 6.12)

```
macsec.c: In function 'macsec_check_offload':
macsec.c:359:48: error: 'struct phy_device' has no member named 'macsec_ops'
 359 | macsec->real_dev->phydev->macsec_ops;
     |                                    ^~
macsec.c:362:40: error: 'struct net_device' has no member named 'macsec_ops'
 362 | macsec->real_dev->macsec_ops;
     |                             ^~
macsec.c: In function '__macsec_get_ops':
macsec.c:382:48: error: 'struct phy_device' has no member named 'macsec_ops'
 382 | return macsec->real_dev->phydev->macsec_ops;
macsec.c:384:40: error: 'struct net_device' has no member named 'macsec_ops'
 384 | return macsec->real_dev->macsec_ops;
macsec.c:385:1: error: control reaches end of non-void function [-Werror=return-type]
cc1: some warnings being treated as errors
```

### Funcións afectadas

- **`macsec_check_offload()`** — Verifica se o hardware NIC soporta aceleración MACsec. Accede a `macsec_ops` en `phydev` e en `net_device`. Como ese campo non existe nos headers RPi, o compilador falla.
- **`__macsec_get_ops()`** — Devolve o punteiro ás operacións hardware MACsec da NIC. Sen `macsec_ops`, o compilador detecta que a función non ten `return` en todos os camiños e lanza `control reaches end of non-void function`.

### Por que Raspberry Pi Foundation eliminou `macsec_ops`

A Raspberry Pi 4B usa un adaptador Ethernet **Broadcom BCM54213** que non ten soporte hardware MACsec. Raspberry Pi Foundation elimina do kernel compoñentes que non son relevantes para o hardware RPi para reducir o tamaño do kernel e os headers. Sen embargo, o código fonte de `macsec.c` no repositorio RPi segue sendo un fork do upstream e mantén as referencias a `macsec_ops`.

---

## 🔄 Intentos fallidos antes do patch

| Intento | Acción | Por que fallou |
|---|---|---|
| 1 | `modprobe macsec` (kernel 6.18.33) | `macsec.ko` non existe no kernel RPi |
| 2 | `apt full-upgrade + reboot` | Non cambiou o kernel, 6.18.33 era o máis recente |
| 3 | Compilar `macsec.c` rama 6.18 con headers do kernel | Erro `macsec_ops` en headers RPi 6.18 |
| 4 | Cambiar a kernel 6.12.75 | Sistema non arrancaba co novo kernel (bootloader non o detectaba automaticamente) |
| 5 | Compilar `macsec.c` rama 6.12 con headers do kernel | Mesmo erro `macsec_ops` en headers RPi 6.12 |
| **6** | **Patch Python + compilar** | **ÉXITO: `macsec.ko` compilado correctamente** |

---

## 🐍 O patch Python: explicación completa

A solución foi modificar o código fonte de `macsec.c` **antes de compilalo**, substituíndo as dúas referencias problemáticas a `macsec_ops` por `NULL`. Isto é seguro porque a RPi 4B non ten hardware MACsec, polo que esas funcións nunca se invocarían en uso real.

### Código completo: `patch_macsec.py`

```python
# patch_macsec.py
# Patch para compilar macsec.ko en kernels Raspberry Pi OS
# Substitúe referencias a macsec_ops (hardware offload) por NULL
# As RPi 4B non teñen hardware MACsec, estas funcións nunca se usan

with open('macsec.c', 'r') as f:
    content = f.read()

# Substitución 1: referencia a macsec_ops a través do PHY device
content = content.replace(
    "macsec->real_dev->phydev->macsec_ops",
    "NULL"
)

# Substitución 2: referencia a macsec_ops directamente en net_device
content = content.replace(
    "macsec->real_dev->macsec_ops",
    "NULL"
)

with open('macsec.c', 'w') as f:
    f.write(content)

print("Patch aplicado correctamente")
```

### Que fai exactamente cada substitución

**Substitución 1:** `macsec->real_dev->phydev->macsec_ops` → `NULL`

`real_dev` é a interface física subyacente (`eth0`). `phydev` é o driver do PHY (Physical Layer device, o chip de capa física do adaptador Ethernet). `macsec_ops` sería o punteiro ás operacións hardware MACsec do PHY. Ao substituílo por `NULL`, a función retorna `NULL` indicando que non hai hardware offload dispoñible → o módulo usa cifrado por software.

**Substitución 2:** `macsec->real_dev->macsec_ops` → `NULL`

Esta referencia accede a `macsec_ops` directamente no `net_device` (a interface de rede). Algúns adaptadores expoñen o hardware offload MACsec a nivel de `net_device` en lugar do PHY. Ao substituír por `NULL`, tamén se cobre este caso. Ademais resolve o erro `control reaches end of non-void function` porque `__macsec_get_ops()` agora ten un `return NULL` explícito en todos os camiños.

### Contexto no código fonte orixinal

```c
// Función macsec_check_offload() en macsec.c (rama rpi-6.12.y):
static bool macsec_check_offload(enum macsec_offload offload,
    struct macsec_dev *macsec)
{
    if (offload == MACSEC_OFFLOAD_PHY && macsec->real_dev->phydev)
        return !!macsec->real_dev->phydev->macsec_ops; // <-- LIÑA PROBLEMÁTICA
    else if (offload == MACSEC_OFFLOAD_MAC)
        return !!macsec->real_dev->macsec_ops;          // <-- LIÑA PROBLEMÁTICA
    return false;
}

// Función __macsec_get_ops() en macsec.c:
static const struct macsec_ops *__macsec_get_ops(...)
{
    if (macsec->real_dev->phydev)
        return macsec->real_dev->phydev->macsec_ops; // <-- LIÑA PROBLEMÁTICA
    return macsec->real_dev->macsec_ops;             // <-- LIÑA PROBLEMÁTICA
    // ERROR: se macsec_ops non existe, o compilador non ve un 'return'
    // válido e lanza: "control reaches end of non-void function"
}

// TRAS O PATCH (substitucións por NULL):
static bool macsec_check_offload(...)
{
    if (offload == MACSEC_OFFLOAD_PHY && macsec->real_dev->phydev)
        return !!NULL; // false -> sen hardware offload
    else if (offload == MACSEC_OFFLOAD_MAC)
        return !!NULL; // false -> sen hardware offload
    return false;
}

static const struct macsec_ops *__macsec_get_ops(...)
{
    if (macsec->real_dev->phydev)
        return NULL; // sen operacións hardware
    return NULL;     // sen operacións hardware -> compila sen erro
}
```

---

## 🛠️ Proceso completo de compilación e instalación

### Paso 1 — Cambiar ao kernel 6.12.75 e instalar headers

```bash
sudo apt install linux-image-6.12.75+rpt-rpi-v8 \
                 linux-headers-6.12.75+rpt-rpi-v8

# Configurar o bootloader para usar o novo kernel
# Engadir en /boot/firmware/config.txt:
# kernel=vmlinuz-6.12.75+rpt-rpi-v8
# initramfs initrd.img-6.12.75+rpt-rpi-v8

sudo cp /boot/vmlinuz-6.12.75+rpt-rpi-v8 /boot/firmware/
sudo cp /boot/initrd.img-6.12.75+rpt-rpi-v8 /boot/firmware/
sudo reboot
```

### Paso 2 — Preparar o directorio e descargar código fonte

```bash
mkdir ~/macsec_module && cd ~/macsec_module

# Descargar macsec.c da rama correcta do kernel RPi
wget https://raw.githubusercontent.com/raspberrypi/linux/refs/heads/rpi-6.12.y/drivers/net/macsec.c

# Verificar descarga
ls -la macsec.c
# Resultado: macsec.c (113756 bytes = 111 KB)
```

### Paso 3 — Crear o Makefile

```bash
cat > Makefile << 'EOF'
obj-m += macsec.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
EOF
```

> `obj-m += macsec.o` indica que `macsec.c` compilarase como módulo externo (`.ko`). A directriz `-C /lib/modules/.../build` usa o sistema de compilación do kernel instalado (headers) para compilar cos mesmos flags que o kernel en uso.

### Paso 4 — Aplicar o patch Python

```bash
python3 patch_macsec.py
# Resultado: Patch aplicado correctamente
```

### Paso 5 — Compilar o módulo

```bash
make
```

Saída esperada de éxito:

```
CC [M]  /home/pi/macsec_module/macsec.o
MODPOST /home/pi/macsec_module/Module.symvers
CC [M]  /home/pi/macsec_module/macsec.mod.o
CC [M]  /home/pi/macsec_module/.module-common.o
LD [M]  /home/pi/macsec_module/macsec.ko

ls -la macsec.ko
# -rw-r--r-- 1 pi pi 458752 Jun 9 09:xx macsec.ko
```

### Paso 6 — Instalar e cargar o módulo

```bash
# Copiar ao directorio de módulos do kernel
sudo cp ~/macsec_module/macsec.ko /lib/modules/$(uname -r)/kernel/drivers/net/

# Actualizar o índice de módulos (IMPRESCINDIBLE)
sudo depmod -a

# Cargar o módulo no kernel
sudo modprobe macsec

# Verificar que está cargado
lsmod | grep macsec
# Resultado: macsec  53248  0
```

### Paso 7 — Configurar carga automática en cada arranque

```bash
echo "macsec" | sudo tee /etc/modules-load.d/macsec.conf
# O servizo systemd-modules-load.service cargará macsec.ko
# automaticamente en cada inicio do sistema
```

---

## ✅ Por que o patch é seguro e correcto

| Aspecto | Sen patch (hardware offload) | Con patch (software puro) |
|---|---|---|
| `macsec_check_offload()` | Comproba se NIC ten hardware MACsec | Devolve `false` sempre (sen hardware) |
| `__macsec_get_ops()` | Devolve punteiro a ops hardware | Devolve `NULL` (sen hardware) |
| Cifrado AES | En NIC hardware (se dispoñible) | En CPU (software, ARMv8 crypto) |
| Funcionalidade MACsec | Completa (con HW accel.) | Completa (sen HW accel.) |
| Impacto en RPi 4B | Ningunha RPi ten NIC MACsec HW | Sen cambio funcional |
| GCM-AES-128 | Dispoñible | Dispoñible (vía ARMv8 crypto inst.) |
| protect / validate / replay | Dispoñible | Dispoñible |
| encrypt on/off | Dispoñible | Dispoñible |

---

## 🔍 Verificación do módulo compilado

```bash
pi@nodoa:~ $ lsmod | grep macsec
macsec          53248  0

pi@nodob:~ $ lsmod | grep macsec
macsec          53248  0
```

> `macsec` = nome do módulo · `53248` = tamaño en bytes · `0` = número de instancias en uso

```bash
pi@nodoa:~ $ ip macsec show
4: macsec0: protect on validate strict sc off sa off encrypt off
    send_sci on end_station off scb off replay off
    cipher suite: GCM-AES-128, using ICV length 16
    TXSC: b827eba848070001 on SA 0
        0: PN 244208, state on, key 01...
    RXSC: b827eb80e8520001, state on
        0: PN 127276, state on, key 02...
    offload: off
```

> `offload: off` confirma modo software puro. `GCM-AES-128` confirma que o cifrado AES de 128 bits está dispoñible e activo.

---

## 📊 Resultados de rendemento

| Métrica | Sen MACsec | Con MACsec (encrypt on) | Overhead |
|---|---|---|---|
| Throughput TCP (iperf3) | 94,4 Mbits/s | 92,5 Mbits/s | **-2,0%** |
| RTT medio (ping ICMP) | 0,666 ms | 0,885 ms | **+33%** |
| Tamaño paquete ICMP | 98 bytes | 130 bytes | +32 bytes |
| Packet loss | 0% | 0% | Sen impacto |

> O overhead do 2% en throughput débese ás instrucións de aceleración criptográfica **ARMv8** integradas no Cortex-A72 da RPi 4B, que executan AES-GCM en hardware dentro da propia CPU.

---

## 📦 Contido do repositorio

```
macsec-rpi4b/
├── patch_macsec.py     # Script Python que aplica o patch en macsec.c
├── Makefile            # Makefile para compilar macsec.ko como módulo externo
└── README.md           # Esta documentación
```

---

## ⚠️ Kernels afectados

O patch é necesario en **calquera kernel Raspberry Pi OS** que non inclúa `macsec_ops` nos headers:

- `rpi-6.18.y` ✗ (confirmado con erros)
- `rpi-6.12.y` ✗ (confirmado con erros) → **usa este con patch** ✓
- Versións anteriores: probablemente afectadas tamén

---

## 📄 Licenza

MIT — libre uso con atribución.

---

## 📚 Referencias

- IEEE Std 802.1AE-2018 — MAC Security
- Dubroca, S. (2016). MACsec: a different solution to encrypt network traffic. Red Hat Developer Blog.
- Ténart, A. (2018). Network traffic encryption in Linux using MACsec. Bootlin Engineering Blog.
- Repositorio kernel RPi: https://github.com/raspberrypi/linux/tree/rpi-6.12.y

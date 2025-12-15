<h1 align="center">Simulador BCI basado en Vectores Poblacionales</h1>

<p align="center">
  <strong>Decodificación de movimiento mediante el algoritmo de Georgopoulos para Interfaces Cerebro-Computadora</strong>
</p>

<p align="center">
  <a href="#descripción">Descripción</a> •
  <a href="#características">Características</a> •
  <a href="#uso">Uso</a> •
  <a href="#resultados">Resultados</a> •
  <a href="#documentación">Documentación</a>
</p>

---

## Descripción

Este proyecto implementa un **simulador computacional de interfaces cerebro-computadora (BCI)** que utiliza el algoritmo de vectores poblacionales de Georgopoulos para decodificar intenciones de movimiento a partir de actividad neuronal simulada.

El simulador modela neuronas de corteza motora con direcciones preferidas, genera trenes de spikes mediante proceso de Poisson, y reconstruye trayectorias circulares en tiempo real mediante decodificación poblacional.

### Objetivos del Proyecto

- Implementar el modelo matemático de codificación direccional neuronal
- Desarrollar un decodificador basado en vectores poblacionales
- Evaluar el efecto de parámetros y arquitecturas neuronales sobre el desempeño
- Validar principios establecidos en la literatura neurocientífica

---

## Características

| Característica | Descripción |
|----------------|-------------|
| Modelo Neuronal | Neuronas con direcciones preferidas y sintonización coseno |
| Generación de Spikes | Proceso estocástico de Poisson biológicamente plausible |
| Decodificación | Algoritmo de vectores poblacionales (Georgopoulos 1986) |
| Visualización | Animación en tiempo real  |
| Configurable | Parámetros ajustables para experimentación |
| Métricas | Error de posición, R², análisis de variabilidad |

---

## Uso

### Ejecución

```bash
python src/DECODIFICADOR_BCI.py
```

### Configuración de Parámetros

Los parámetros se pueden modificar directamente en el archivo `DECODIFICADOR_BCI.py`:

```python
# Parámetros de la población neuronal
N_NEURONAS = 200              # Número de neuronas
DISTRIBUCION = 'uniforme'     # 'uniforme', 'sesgada', 'agrupada'

# Parámetros del modelo neuronal
R0 = 20.0                     # Tasa de disparo base (Hz)
K = 10                        # Factor de modulación

# Parámetros del decodificador
GANANCIA_DECODIFICACION = 0.25
VENTANA = 0.5                 # Ventana temporal (segundos)
ALPHA_SUAVIZADO = 0.5         # Factor de suavizado exponencial

# Parámetros de la trayectoria
RADIO = 0.6                   # Radio del círculo (metros)
PERIODO = 12.0                # Período del movimiento (segundos)
```

### Distribuciones Disponibles

| Distribución | Descripción | Uso Recomendado |
|--------------|-------------|-----------------|
| `uniforme` | Cobertura isotrópica completa | Caso ideal, mejor desempeño |
| `sesgada` | Concentrada en una dirección | Simular colocación subóptima de electrodos |
| `agrupada` | 4 clusters en direcciones cardinales | Organización modular tipo columnas corticales |

---

## Resultados

### Parámetros Optimizados

Mediante análisis paramétrico sistemático (930 simulaciones), se determinó la configuración óptima:

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| r₀ (tasa basal) | 20 Hz | Realismo biológico (rango típico 10-50 Hz) |
| k (modulación) | 10 | Balance señal robusta/realismo (R²=0.802) |
| Ganancia | 0.25 | Estabilidad sobre error mínimo absoluto |
| Ventana temporal | 0.5 s | Mínimo error (0.3592 m), R²=0.696 |
| α (suavizado) | 0.5 | Balance óptimo suavidad/responsividad |

### Desempeño por Arquitectura (200 neuronas)

| Distribución | Error (m) | R² | Variabilidad |
|--------------|-----------|-----|--------------|
| Uniforme | 0.426 ± 0.006 | 0.476 | 1.4% |
| Agrupada | 0.430 ± 0.009 | 0.482 | 2.1% |
| Sesgada | 1.417 ± 0.108 | 0.043 | 7.6% |

### Hallazgos Principales

> **Hallazgo clave:** La distribución espacial de direcciones preferidas impacta el desempeño **3.3× más** que el tamaño poblacional.

- Distribuciones balanceadas (uniforme/agrupada) logran desempeño equivalente
- Rendimientos decrecientes más allá de 100-200 neuronas
- 50-100 neuronas bien distribuidas son suficientes para control 2D básico
- El sesgo direccional no se compensa agregando más neuronas

---

## Estructura del Proyecto

```
BCI-Population-Vector-Simulator/
│
├── README.md                 # Este archivo
│
├── src/
│   └── DECODIFICADOR_BCI.py      # Código principal del simulador
│
└── docs/
    └── BCI_FINAL(1).pdf         # Artículo completo
```

---

## Documentación

### Modelo Matemático

El simulador implementa el modelo de sintonización direccional de Georgopoulos:

$$r(t) = r_0 + k \cdot (\hat{p}_i \cdot \vec{v}(t))$$

Donde:
- $r(t)$: Tasa de disparo instantánea
- $r_0$: Tasa basal (20 Hz)
- $k$: Factor de modulación (10)
- $\hat{p}_i$: Vector unitario de dirección preferida
- $\vec{v}(t)$: Vector de velocidad del movimiento

### Algoritmo de Decodificación

El vector poblacional se calcula como:

$$\vec{P} = \sum_{i} (r_i - r_0) \cdot \hat{p}_i$$

La velocidad decodificada se obtiene mediante:

$$\vec{v}_{dec} = G \cdot \frac{\vec{P}}{||\vec{P}||}$$

---

## Referencias

1. **Georgopoulos, A. P., et al.** (1982). On the relations between the direction of two-dimensional arm movements and cell discharge in primate motor cortex. *Journal of Neuroscience*, 2(11), 1527-1537.

2. **Georgopoulos, A. P., Schwartz, A. B., & Kettner, R. E.** (1986). Neuronal population coding of movement direction. *Science*, 233(4771), 1416-1419.

3. **Schwartz, A. B.** (1994). Direct cortical representation of drawing. *Science*, 265(5171), 540-542.

4. **Serruya, M. D., et al.** (2002). Instant neural control of a movement signal. *Nature*, 416(6877), 141-142.

5. **Softky, W. R., & Koch, C.** (1993). The highly irregular firing of cortical cells is inconsistent with temporal integration of random EPSPs. *Journal of Neuroscience*, 13(1), 334-350.

---

## Autores

| Rios Ordaz Alejandro | Colina Crisanto Cristobal | Avendaño Diaz Carlos | Hernandez Roman Christian |
|:---------------:|:----------------:|:-------------------:|:--------------:|

**Universidad Veracruzana**  
Facultad de Instrumentación Electrónica  
Ingeniería Biomédica

*Temas Selectos IB II: Simulación de Sistemas Biológicos*

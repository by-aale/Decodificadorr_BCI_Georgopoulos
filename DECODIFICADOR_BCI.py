
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from openpyxl import Workbook


N_NEURONAS = 200  # Número de neuronas en la población
DISTRIBUCION = 'uniforme'  
#PARAMETROS DEL SISTEMA
DT = 0.02              # Paso de tiempo (20ms) - resolución temporal de la simulación
T_TOTAL = 20.0         # Tiempo total de simulación (20 segundos)
R0 = 20.0              # Tasa de disparo base (Hz) - cuando no hay modulación direccional
K = 10               # Factor de modulación - qué tanto cambia la tasa con la dirección 
TASA_MAXIMA = 180.0    # Tasa máxima de disparo permitida (Hz) - límite fisiológico
GANANCIA_DECODIFICACION = 0.25  # Factor para convertir vector poblacional a velocidad 
VENTANA = 0.5          # Ventana temporal para estimar tasas (segundos) 
RADIO = 0.6            # Radio de la trayectoria circular (metros)
PERIODO = 12.0         # Periodo del movimiento circular (segundos)

# Parámetro de suavizado del cursor
ALPHA_SUAVIZADO = 0.5  # Factor de suavizado exponencial

# =============================================================================


print("DECODIFICADOR BCI")
print(f"\n Configuración:")
print(f"   • Neuronas: {N_NEURONAS}")
print(f"   • Distribución: {DISTRIBUCION}")
print(f"   • R0 (tasa base): {R0} Hz")
print(f"   • K (modulación): {K}")
print(f"   • Ganancia decodificación: {GANANCIA_DECODIFICACION}")
print(f"   • Ventana temporal: {VENTANA}s")


# Crear el vector de tiempo para toda la simulación
tiempo = np.arange(0, T_TOTAL, DT)

# =============================================================================
# GENERAR TRAYECTORIA CIRCULAR DE REFERENCIA
# =============================================================================
# La trayectoria objetivo es un círculo que el cursor debe seguir
# Usamos paramétricas: x(t) = R*cos(ωt), y(t) = R*sin(ωt)

omega = 2 * np.pi / PERIODO  # Frecuencia angular (rad/s)
trayectoria = np.zeros((len(tiempo), 2))  # Matriz para guardar posiciones [x, y]
vel_trayectoria = np.zeros((len(tiempo), 2))  # Matriz para guardar velocidades [vx, vy]

# Calcular cada punto de la trayectoria circular
for idx, t in enumerate(tiempo):
    trayectoria[idx] = [RADIO * np.cos(omega * t), RADIO * np.sin(omega * t)]

# Calcular velocidades usando diferencias finitas
vel_trayectoria[0:-1] = (trayectoria[1:] - trayectoria[:-1]) / DT
vel_trayectoria[-1] = vel_trayectoria[-2]  # Copiar el último valor

# =============================================================================
# CREAR POBLACIÓN NEURONAL CON DIRECCIONES PREFERIDAS
# =============================================================================
# Cada neurona tiene una "dirección preferida" - dispara más cuando el movimiento
# va en esa dirección (principio de codificación direccional de Georgopoulos)

if DISTRIBUCION == 'uniforme':
    # Distribución uniforme: neuronas cubren todas las direcciones por igual
    angulos = np.linspace(0, 2*np.pi, N_NEURONAS, endpoint=False)
    angulos += np.random.normal(0, 0.03, N_NEURONAS)  # Pequeño ruido para realismo
    
elif DISTRIBUCION == 'sesgada':
    # Distribución sesgada: mayoría de neuronas prefieren una dirección
    angulos = np.random.normal(0, np.pi/3, N_NEURONAS)
    
elif DISTRIBUCION == 'agrupada':
    # Distribución en clusters: neuronas agrupadas en 4 direcciones cardinales
    centros_clusters = [0, np.pi/2, np.pi, 3*np.pi/2]  # 0°, 90°, 180°, 270°
    angulos = []
    for centro in centros_clusters:
        # Crear un cluster de neuronas alrededor de cada dirección cardinal
        angulos.extend(np.random.normal(centro, np.pi/8, N_NEURONAS//4))
    angulos = np.array(angulos)

# Normalizar ángulos al rango [0, 2π]
angulos = np.mod(angulos, 2*np.pi)

# Convertir ángulos a vectores unitarios de dirección preferida
dirs_preferidas = np.column_stack((np.cos(angulos), np.sin(angulos)))

# =============================================================================
# SIMULACIÓN PRINCIPAL - GENERACIÓN DE SPIKES Y DECODIFICACIÓN
# =============================================================================


# Inicializar variables de estado del cursor
posiciones_cursor = []  # Almacenará toda la trayectoria decodificada
pos_cursor = np.array([0.0, 0.0])  # Posición inicial en el origen
vel_cursor = np.array([0.0, 0.0])  # Velocidad inicial (para suavizado)

# Matriz para almacenar todos los spikes: [neurona × tiempo]
trenes_spikes = np.zeros((N_NEURONAS, len(tiempo)), dtype=int)

# Calcular cuántos pasos de tiempo hay en la ventana de estimación
pasos_ventana = max(1, int(VENTANA / DT))

# BUCLE PRINCIPAL: simular cada paso de tiempo
for idx_t in range(len(tiempo)):
    # Obtener la velocidad objetivo en este instante
    v_objetivo = vel_trayectoria[idx_t]
    
    # --- PASO 1: CALCULAR TASAS DE DISPARO ---
    # Cada neurona modula su tasa según qué tan alineado está v_objetivo con su dirección preferida
    # Ecuación: r(t) = R0 + K * (dir_preferida · v_objetivo)
    proyeccion = dirs_preferidas.dot(v_objetivo)  # Producto punto con cada dirección
    tasa_t = R0 + K * proyeccion  # Aplicar modelo de sintonización coseno
    tasa_t = np.clip(tasa_t, 0, TASA_MAXIMA)  # Limitar a rango fisiológico [0, MAX]
    
    # --- PASO 2: GENERAR SPIKES ---
    # Usar proceso de Poisson: probabilidad de spike = tasa * dt
    prob_spike = np.clip(tasa_t * DT, 0, 1)  # Probabilidad debe estar en [0,1]
    spikes = np.random.rand(N_NEURONAS) < prob_spike  # Comparar con número aleatorio
    trenes_spikes[:, idx_t] = spikes.astype(int)  # Guardar: 1=spike, 0=sin spike
    
    # --- PASO 3: ESTIMAR TASAS EN VENTANA TEMPORAL ---
    # Para reducir ruido, contamos spikes en una ventana reciente y estimamos la tasa
    inicio = max(0, idx_t - pasos_ventana + 1)  # Inicio de la ventana
    duracion_ventana = (idx_t - inicio + 1) * DT  # Duración real de la ventana
    conteos = trenes_spikes[:, inicio:idx_t+1].sum(axis=1)  # Contar spikes por neurona
    tasa_estimada = conteos / duracion_ventana  # Convertir conteos a tasa (Hz)
    
    # --- PASO 4: DECODIFICACIÓN MEDIANTE VECTOR POBLACIONAL (Georgopoulos) ---
    # Idea: cada neurona "vota" por su dirección preferida, ponderado por su modulación
    
    # Calcular modulación = cuánto se desvía cada neurona de su tasa base
    modulacion = tasa_estimada - R0
    
    # Filtrar: solo usar neuronas con modulación positiva (activas)
    mascara_activa = modulacion > 0
    
    if np.any(mascara_activa):
        # Calcular vector poblacional como suma ponderada de direcciones preferidas
        suma_ponderada = np.sum(modulacion[mascara_activa][:, None] * dirs_preferidas[mascara_activa], axis=0)
        peso_total = np.sum(modulacion[mascara_activa])
        vector = suma_ponderada / (peso_total + 1e-12)  # Normalizar (evitar división por 0)
    else:
        # Si no hay neuronas activas, no hay movimiento
        vector = np.zeros(2)
    
    # Convertir el vector poblacional a velocidad decodificada
    vel_decodificada = GANANCIA_DECODIFICACION * vector
    
    # --- PASO 5: SUAVIZADO EXPONENCIAL ---
    # Reducir jitter combinando velocidad actual con la previa
    # Formula: v_nueva = α * v_decodificada + (1-α) * v_previa
    vel_cursor = ALPHA_SUAVIZADO * vel_decodificada + (1 - ALPHA_SUAVIZADO) * vel_cursor
    
    # --- PASO 6: INTEGRAR VELOCIDAD PARA OBTENER POSICIÓN ---
    # Usar integración de Euler: posición_nueva = posición_anterior + velocidad * dt
    pos_cursor = pos_cursor + vel_cursor * DT
    posiciones_cursor.append(pos_cursor.copy())  # Guardar en historial

# Convertir lista a array para facilitar operaciones
posiciones_cursor = np.array(posiciones_cursor)
print("Simulación completada")

# =============================================================================
# MÉTRICAS DE DESEMPEÑO
# =============================================================================

print("\n MÉTRICAS DE DESEMPEÑO:")

# Calcular error de posición en cada instante
error_pos = np.linalg.norm(trayectoria - posiciones_cursor, axis=1)
error_medio = np.mean(error_pos)
error_std = np.std(error_pos)

print(f"   • Error promedio: {error_medio:.4f} m")
print(f"   • Desviación estándar: {error_std:.4f} m")
print(f"   • Error máximo: {np.max(error_pos):.4f} m")
print(f"   • Error final: {error_pos[-1]:.4f} m")


# Analizar qué tan bien seguimos las velocidades
vel_decodificada_array = np.diff(posiciones_cursor, axis=0) / DT  # Calcular de posiciones
vel_real = vel_trayectoria[:-1]  # Velocidad objetivo (sincronizar tamaños)

# Calcular coeficiente de determinación R² para cada componente
# R² = 1 indica ajuste perfecto, R² = 0 indica predicción no mejor que la media
r2_x = 1 - np.sum((vel_real[:, 0] - vel_decodificada_array[:, 0])**2) / (np.var(vel_real[:, 0]) * len(vel_real[:, 0]) + 1e-12)
r2_y = 1 - np.sum((vel_real[:, 1] - vel_decodificada_array[:, 1])**2) / (np.var(vel_real[:, 1]) * len(vel_real[:, 1]) + 1e-12)

print(f"   • R² velocidad X: {r2_x:.3f}")
print(f"   • R² velocidad Y: {r2_y:.3f}")

# =============================================================================
# ANIMACIÓN EN TIEMPO REAL
# =============================================================================


fig, ax = plt.subplots(figsize=(10, 10))
ax.set_xlim(-RADIO*1.5, RADIO*1.5)
ax.set_ylim(-RADIO*1.5, RADIO*1.5)
ax.set_aspect('equal', 'box')
ax.grid(True, alpha=0.3, linewidth=0.5)
ax.set_facecolor('#f8f9fa')

# Crear elementos gráficos
linea_objetivo, = ax.plot([], [], 'b-', linewidth=4, label='Trayectoria Objetivo', alpha=0.6)
linea_cursor, = ax.plot([], [], 'r-', linewidth=3, label='Trayectoria Decodificada', alpha=0.9)
punto_objetivo, = ax.plot([], [], 'o', color='blue', markersize=15, zorder=5)
punto_cursor, = ax.plot([], [], 'o', color='red', markersize=15, zorder=5)
ax.plot([0], [0], 'o', color='green', markersize=20, label='Inicio', zorder=4)

# Textos informativos
texto_tiempo = ax.text(0.02, 0.96, '', transform=ax.transAxes, fontsize=14, 
                    fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

texto_error = ax.text(0.02, 0.90, '', transform=ax.transAxes, fontsize=12,
                     bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

ax.legend(loc='upper right', fontsize=13, framealpha=0.95)
ax.set_xlabel('Posición X (m)', fontsize=13, fontweight='bold')
ax.set_ylabel('Posición Y (m)', fontsize=13, fontweight='bold')

# Funciones de animación
def init():
    """Inicializar elementos de la animación"""
    linea_objetivo.set_data([], [])
    linea_cursor.set_data([], [])
    punto_objetivo.set_data([], [])
    punto_cursor.set_data([], [])
    texto_tiempo.set_text('')
    texto_error.set_text('')
    return linea_objetivo, linea_cursor, punto_objetivo, punto_cursor, texto_tiempo, texto_error

def animar_cuadro(i):
    """Actualizar animación para el cuadro i"""
    linea_objetivo.set_data(trayectoria[:i+1, 0], trayectoria[:i+1, 1])
    linea_cursor.set_data(posiciones_cursor[:i+1, 0], posiciones_cursor[:i+1, 1])
    punto_objetivo.set_data([trayectoria[i, 0]], [trayectoria[i, 1]])
    punto_cursor.set_data([posiciones_cursor[i, 0]], [posiciones_cursor[i, 1]])
    texto_tiempo.set_text(f't = {tiempo[i]:.2f}s / {T_TOTAL:.0f}s')
    texto_error.set_text(f'Error: {error_pos[i]:.3f} m')
    return linea_objetivo, linea_cursor, punto_objetivo, punto_cursor, texto_tiempo, texto_error

# Crear la animación
animacion = animation.FuncAnimation(fig, animar_cuadro, init_func=init, 
                              frames=len(tiempo), interval=DT*1000, 
                              blit=True, repeat=True)

plt.title(f'Decodificador BCI: {N_NEURONAS} neuronas | {DISTRIBUCION.upper()}\nError medio: {error_medio:.3f}m', 
          fontsize=16, fontweight='bold', pad=20)

plt.tight_layout()
plt.show()

# =============================================================================
# GRÁFICOS DE ANÁLISIS DETALLADO (SIN ERROR NI R2)
# =============================================================================

fig_analisis, ejes = plt.subplots(1, 2, figsize=(15, 6))

# --- GRÁFICO 1: Trayectorias completas ---
ax1 = ejes[0]
ax1.plot(trayectoria[:, 0], trayectoria[:, 1], 'b-', linewidth=4, label='Objetivo', alpha=0.6)
ax1.plot(posiciones_cursor[:, 0], posiciones_cursor[:, 1], 'r-', linewidth=3, 
         label='Decodificada', alpha=0.9)
ax1.plot([0], [0], 'go', markersize=15, label='Inicio', zorder=5)
ax1.set_aspect('equal')
ax1.grid(True, alpha=0.3)
ax1.legend(fontsize=11)
ax1.set_title(f'Trayectorias Completas\nError medio: {error_medio:.3f}m', fontweight='bold')
ax1.set_xlabel('X (m)')
ax1.set_ylabel('Y (m)')

# --- GRÁFICO 2: Distribución de direcciones preferidas ---
ax2 = ejes[1]
ax2.scatter(dirs_preferidas[:, 0], dirs_preferidas[:, 1], c=np.arange(N_NEURONAS), 
            cmap='hsv', s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
circulo = plt.Circle((0, 0), 1, fill=False, color='black', linewidth=2, linestyle='--')
ax2.add_patch(circulo)
ax2.set_xlim(-1.2, 1.2)
ax2.set_ylim(-1.2, 1.2)
ax2.set_aspect('equal')
ax2.grid(True, alpha=0.3)
ax2.set_title(f'Direcciones Preferidas ({N_NEURONAS} neuronas)', fontweight='bold')
ax2.set_xlabel('Componente X')
ax2.set_ylabel('Componente Y')

plt.suptitle(f'ANÁLISIS COMPLETO - Decodificador BCI\n{N_NEURONAS} neuronas | {DISTRIBUCION.upper()}', 
             fontsize=18, fontweight='bold', y=0.98)

plt.tight_layout()

# Guardar figura
nombre_archivo = f'bci_analisis_{DISTRIBUCION}_{N_NEURONAS}n.png'
plt.savefig(nombre_archivo, dpi=300, bbox_inches='tight')
print(f"Gráficos guardados: {nombre_archivo}")
plt.show()


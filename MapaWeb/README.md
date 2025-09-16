# Mapa Interactivo de Clasificación por Provincia

Aplicación web interactiva para visualizar datos de clasificación de cobertura terrestre por provincia en Argentina.

## Estructura del Proyecto

```
MapaWeb/
├── index.html          # Página principal
├── styles.css          # Estilos CSS
├── app.js             # Lógica de la aplicación
└── README.md          # Documentación
```

## Características

- **Mapa Interactivo**: Visualización de provincias argentinas con Leaflet
- **Gráficos Dinámicos**: Gráficos de barras por provincia usando Chart.js
- **Leyenda de Clasificaciones**: Referencia visual de las 9 categorías
- **Gráfico de Máximos**: Muestra qué provincia tiene el máximo de cada clasificación
- **Diseño Responsivo**: Adaptable a diferentes tamaños de pantalla

## Tecnologías Utilizadas

- **HTML5**: Estructura semántica
- **CSS3**: Estilos modernos con gradientes y animaciones
- **JavaScript ES6+**: Programación orientada a objetos
- **Leaflet**: Biblioteca de mapas interactivos
- **Chart.js**: Gráficos dinámicos

## Uso

1. Abrir `index.html` en un navegador web
2. Los datos se cargan automáticamente desde `../outputs_analysis/`
3. Hacer clic en cualquier provincia para ver su análisis detallado

## Requisitos

- Navegador web moderno con soporte para ES6+
- Conexión a internet (para cargar Leaflet y Chart.js)
- Archivos de datos en la carpeta `../outputs_analysis/`

## Datos Requeridos

- `datos_visualizacion_real.json`
- `maximos_por_clasificacion.json`
- `provincias_estadisticas_real.geojson`

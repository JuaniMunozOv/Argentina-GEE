class MapaProvincias {
    constructor() {
        this.map = null;
        this.datosProvincias = null;
        this.clasificaciones = null;
        this.provinciasLayer = null;
        this.chart = null;

        this.init();
    }

    async init() {
        try {
            await this.cargarDatos();
            if (this.datosProvincias && this.clasificaciones) {
                this.inicializarMapa();
                this.crearLeyenda();
            } else {
                console.error('Error cargando datos. Verifica que el archivo datos_visualizacion_real.json existe.');
            }
        } catch (error) {
            console.error('Error inicializando:', error);
        }
    }

    async cargarDatos() {
        try {
            const response = await fetch('../outputs_analysis/datos_visualizacion_real.json');
            const data = await response.json();
            this.datosProvincias = data.provincias;
            this.clasificaciones = data.clasificaciones;

            const maximosResponse = await fetch('../outputs_analysis/maximos_por_clasificacion.json');
            const maximosData = await maximosResponse.json();

            this.crearGraficoMaximos(maximosData);

            console.log('Datos cargados exitosamente');
            return data;
        } catch (error) {
            console.error('Error cargando datos:', error);
            throw error;
        }
    }

    inicializarMapa() {
        this.map = L.map('map').setView([-38.4161, -63.6167], 4);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(this.map);

        this.agregarMarcadoresProvincias();
    }

    agregarMarcadoresProvincias() {
        if (!this.datosProvincias) return;

        this.provinciasLayer = L.geoJSON(this.datosProvincias, {
            pointToLayer: (feature, latlng) => {
                const props = feature.properties;
                const clasificaciones = props.clasificaciones;

                let claseDominante = null;
                let maxPorcentaje = 0;

                for (const [nombre, datos] of Object.entries(clasificaciones)) {
                    if (datos.porcentaje > maxPorcentaje) {
                        maxPorcentaje = datos.porcentaje;
                        claseDominante = datos.color;
                    }
                }

                return L.circleMarker(latlng, {
                    radius: 12,
                    fillColor: claseDominante || '#3388ff',
                    color: '#fff',
                    weight: 3,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            },
            onEachFeature: (feature, layer) => {
                const props = feature.properties;
                const clasificaciones = props.clasificaciones;

                let claseDominante = null;
                let maxPorcentaje = 0;

                for (const [nombre, datos] of Object.entries(clasificaciones)) {
                    if (datos.porcentaje > maxPorcentaje) {
                        maxPorcentaje = datos.porcentaje;
                        claseDominante = nombre;
                    }
                }

                const popupContent = `
                    <div class="popup-content">
                        <button class="popup-close" onclick="this.parentElement.parentElement.closePopup()">&times;</button>
                        <div class="popup-title">${props.provincia}</div>
                        <div class="popup-info">
                            <strong>Área:</strong> ${props.area_total_km2.toLocaleString()} km²<br>
                            <strong>Píxeles:</strong> ${props.total_pixels.toLocaleString()}<br>
                            <strong>Clase dominante:</strong> ${claseDominante} (${maxPorcentaje.toFixed(1)}%)
                        </div>
                        <div class="popup-chart">
                            <canvas id="chart-${props.provincia.replace(/\s+/g, '-')}"></canvas>
                        </div>
                    </div>
                `;

                layer.bindPopup(popupContent, {
                    maxWidth: 500,
                    className: 'custom-popup'
                });

                layer.on('popupopen', () => {
                    setTimeout(() => {
                        this.crearGraficoEnPopup(props.provincia, clasificaciones);
                    }, 100);
                });
            }
        }).addTo(this.map);
    }


    crearGraficoEnPopup(provinciaNombre, clasificaciones) {
        const canvasId = `chart-${provinciaNombre.replace(/\s+/g, '-')}`;
        const canvas = document.getElementById(canvasId);

        if (!canvas) return;

        if (this.chart) {
            this.chart.destroy();
        }

        const datos = Object.entries(clasificaciones)
            .map(([nombre, datos]) => ({
                nombre: nombre,
                area: datos.area_km2,
                porcentaje: datos.porcentaje,
                color: datos.color
            }))
            .sort((a, b) => b.area - a.area);

        const labels = datos.map(d => d.nombre);
        const areas = datos.map(d => d.area);
        const colores = datos.map(d => d.color);

        this.chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Área (km²)',
                    data: areas,
                    backgroundColor: colores,
                    borderColor: colores,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Distribución Real - ${provinciaNombre}`,
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function (context) {
                                const porcentaje = datos[context.dataIndex].porcentaje;
                                return `Porcentaje: ${porcentaje.toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Área (km²)',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            font: {
                                size: 11
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Clasificación',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
    }

    crearGraficoMaximos(maximosData) {
        const container = document.getElementById('maximosItems');
        container.innerHTML = '';

        const sortedMaximos = Object.entries(maximosData)
            .sort(([, a], [, b]) => b.porcentaje - a.porcentaje);

        sortedMaximos.forEach(([clase, datos]) => {
            const item = document.createElement('div');
            item.className = 'maximo-item';
            item.style.borderLeftColor = datos.color;

            item.innerHTML = `
                <div class="maximo-color" style="background-color: ${datos.color}"></div>
                <div class="maximo-text">
                    <div>
                        <div class="maximo-clase">${clase}</div>
                        <div class="maximo-provincia">${datos.provincia}</div>
                    </div>
                    <div class="maximo-porcentaje">${datos.porcentaje}%</div>
                </div>
            `;

            container.appendChild(item);
        });
    }

    crearLeyenda() {
        const container = document.getElementById('legendItems');
        container.innerHTML = '';

        if (!this.clasificaciones) return;

        const sortedClases = Object.entries(this.clasificaciones)
            .sort(([, a], [, b]) => a.nombre.localeCompare(b.nombre));

        sortedClases.forEach(([id, clase]) => {
            const item = document.createElement('div');
            item.className = 'legend-item';

            item.innerHTML = `
                <div class="legend-color" style="background-color: ${clase.color}"></div>
                <span>${clase.nombre}</span>
            `;

            container.appendChild(item);
        });
    }
}

// Inicializar la aplicación cuando se carga el DOM
document.addEventListener('DOMContentLoaded', () => {
    new MapaProvincias();
});

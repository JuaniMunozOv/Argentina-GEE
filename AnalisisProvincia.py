#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import json
import warnings
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

@dataclass
class Configuracion:
    raster_input: str = "Argentina-Class-Recortada.tif"
    provincias_shapefile: str = "Provincias/provinciaPolygon.shp"
    output_directory: str = "outputs_analysis"
    
    class_info: Dict[int, Tuple[str, str]] = None
    
    def __post_init__(self):
        if self.class_info is None:
            self.class_info = {
                47:  ("Agua",                   "#419bdf"),
                57:  ("Bosques",                "#397d49"),
                122: ("Pastizales",            "#7a87c6"),
                136: ("Matorrales",            "#88b053"),
                165: ("Suelo Desnudo",         "#a59b8f"),
                179: ("Nieve y Hielo",         "#b39fe1"),
                196: ("Áreas Urbanas",         "#c4281b"),
                223: ("Vegetación Inundable",   "#dfc35a"),
                228: ("Tierras de Cultivo",    "#e49635")
            }

@dataclass
class Provincia:
    nombre: str
    geometry: Any
    id: int

@dataclass
class EstadisticasProvincia:
    provincia: str
    area_km2: float
    total_pixels: int
    clasificaciones: Dict[str, Dict[str, Any]]

class LectorDatos(ABC):
    @abstractmethod
    def leer_provincias(self) -> List[Provincia]:
        pass

class LectorShapefile(LectorDatos):
    def __init__(self, config: Configuracion):
        self.config = config
    
    def leer_provincias(self) -> List[Provincia]:
        try:
            import fiona
            from shapely.geometry import shape
            
            provincias = []
            with fiona.open(self.config.provincias_shapefile) as src:
                for i, feature in enumerate(src):
                    try:
                        geom = shape(feature['geometry'])
                        props = feature['properties']
                        
                        nombre = self._extraer_nombre_provincia(props, i)
                        
                        provincias.append(Provincia(
                            nombre=nombre,
                            geometry=geom,
                            id=i
                        ))
                        
                    except Exception as e:
                        logging.warning(f"Error procesando provincia {i}: {e}")
                        continue
            
            return provincias
            
        except Exception as e:
            logging.error(f"Error leyendo shapefile: {e}")
            return []
    
    def _extraer_nombre_provincia(self, props: Dict, indice: int) -> str:
        campos_nombre = ['Provincia', 'NAME_1', 'NOMBRE', 'prov_name', 'provincia', 'nombre', 'name', 'NAME', 'fna']
        
        for campo in campos_nombre:
            if campo in props and props[campo]:
                return str(props[campo]).strip()
        
        return f"Provincia_{indice}"

class ProcesadorRaster(ABC):
    @abstractmethod
    def procesar_provincia(self, raster_path: str, geometry: Any, nombre_provincia: str) -> Optional[EstadisticasProvincia]:
        pass

class ProcesadorRasterio(ProcesadorRaster):
    def __init__(self, config: Configuracion):
        self.config = config
    
    def procesar_provincia(self, raster_path: str, geometry: Any, nombre_provincia: str) -> Optional[EstadisticasProvincia]:
        try:
            import rasterio
            from rasterio.mask import mask
            from shapely.geometry import mapping
            
            with rasterio.open(raster_path) as src:
                try:
                    masked_data, _ = mask(src, [mapping(geometry)], crop=True, nodata=0)
                    masked_data = masked_data[0]
                    
                    if masked_data.size == 0:
                        logging.warning(f"No hay datos para {nombre_provincia}")
                        return None
                    
                    return self._calcular_estadisticas(masked_data, nombre_provincia, src.res[0] * src.res[1])
                    
                except Exception as e:
                    logging.warning(f"Error enmascarando datos para {nombre_provincia}: {e}")
                    return None
                    
        except Exception as e:
            logging.error(f"Error procesando {nombre_provincia}: {e}")
            return None
    
    def _calcular_estadisticas(self, data: np.ndarray, nombre_provincia: str, pixel_area_km2: float) -> EstadisticasProvincia:
        valid_pixels = data[data > 0]
        total_pixels = len(valid_pixels)
        
        if total_pixels == 0:
            return EstadisticasProvincia(
                provincia=nombre_provincia,
                area_km2=0.0,
                total_pixels=0,
                clasificaciones={}
            )
        
        stats = {}
        for class_id, (class_name, color) in self.config.class_info.items():
            count = np.sum(valid_pixels == class_id)
            area_km2 = count * pixel_area_km2
            percentage = (count / total_pixels) * 100
            
            stats[class_name] = {
                "area_km2": float(round(area_km2, 2)),
                "porcentaje": float(round(percentage, 2)),
                "color": color
            }
        
        total_area = total_pixels * pixel_area_km2
        
        return EstadisticasProvincia(
            provincia=nombre_provincia,
            area_km2=float(round(total_area, 2)),
            total_pixels=int(total_pixels),
            clasificaciones=stats
        )

class GeneradorSalida(ABC):
    @abstractmethod
    def generar_salidas(self, estadisticas: List[EstadisticasProvincia], config: Configuracion) -> None:
        pass

class GeneradorJSON(GeneradorSalida):
    def generar_salidas(self, estadisticas: List[EstadisticasProvincia], config: Configuracion) -> None:
        self._crear_directorio_salida(config.output_directory)
        
        datos_visualizacion = self._crear_datos_visualizacion(estadisticas, config)
        geojson_data = self._crear_geojson(estadisticas, config)
        
        self._guardar_json(datos_visualizacion, config.output_directory, "datos_visualizacion_real.json")
        self._guardar_json(geojson_data, config.output_directory, "provincias_estadisticas_real.geojson")
        
        self._generar_csv(estadisticas, config)
        self._generar_maximos(estadisticas, config)
    
    def _crear_directorio_salida(self, output_dir: str) -> None:
        Path(output_dir).mkdir(exist_ok=True)
    
    def _crear_datos_visualizacion(self, estadisticas: List[EstadisticasProvincia], config: Configuracion) -> Dict:
        clasificaciones = {}
        for class_id, (nombre, color) in config.class_info.items():
            clasificaciones[str(class_id)] = {"nombre": nombre, "color": color}
        
        features = []
        for i, stats in enumerate(estadisticas):
            if stats is None:
                continue
            
            coords = self._obtener_coordenadas_provincia(i)
            feature = {
                "type": "Feature",
                "properties": {
                    "provincia": stats.provincia,
                    "area_total_km2": float(round(stats.area_km2, 2)),
                    "total_pixels": int(stats.total_pixels),
                    "clasificaciones": {}
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(coords[0]), float(coords[1])]
                }
            }
            
            for class_name, color in config.class_info.values():
                feature["properties"]["clasificaciones"][class_name] = {
                    "area_km2": float(round(stats.clasificaciones.get(class_name, {}).get("area_km2", 0), 2)),
                    "porcentaje": float(round(stats.clasificaciones.get(class_name, {}).get("porcentaje", 0), 2)),
                    "color": color
                }
            
            features.append(feature)
        
        return {
            "clasificaciones": clasificaciones,
            "provincias": {
                "type": "FeatureCollection",
                "features": features
            }
        }
    
    def _crear_geojson(self, estadisticas: List[EstadisticasProvincia], config: Configuracion) -> Dict:
        features = []
        for i, stats in enumerate(estadisticas):
            if stats is None:
                continue
            
            coords = self._obtener_coordenadas_provincia(i)
            feature = {
                "type": "Feature",
                "properties": {
                    "provincia": stats.provincia,
                    "area_total_km2": float(round(stats.area_km2, 2)),
                    "total_pixels": int(stats.total_pixels),
                    "clasificaciones": {}
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(coords[0]), float(coords[1])]
                }
            }
            
            for class_name, color in config.class_info.values():
                feature["properties"]["clasificaciones"][class_name] = {
                    "area_km2": float(round(stats.clasificaciones.get(class_name, {}).get("area_km2", 0), 2)),
                    "porcentaje": float(round(stats.clasificaciones.get(class_name, {}).get("porcentaje", 0), 2)),
                    "color": color
                }
            
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    def _obtener_coordenadas_provincia(self, indice: int) -> Tuple[float, float]:
        coordenadas_capitales = [
            (-58.3816, -34.6037), (-58.3731, -34.6118), (-65.2071, -28.4681),
            (-60.4300, -27.4514), (-65.1033, -43.7889), (-64.1888, -31.4201),
            (-58.8309, -27.4692), (-60.4300, -32.0581), (-58.1836, -26.1775),
            (-65.3014, -24.1858), (-64.2833, -36.6167), (-66.8504, -29.4131),
            (-68.8272, -32.9442), (-55.4026, -27.3621), (-68.0595, -38.9516),
            (-67.3314, -41.1335), (-65.2071, -24.7821), (-68.5364, -31.5375),
            (-66.3354, -33.2950), (-69.2167, -51.6230), (-60.6396, -32.9442),
            (-64.2903, -27.7824), (-68.3044, -54.8019), (-65.2071, -26.8241)
        ]
        
        if indice < len(coordenadas_capitales):
            return coordenadas_capitales[indice]
        else:
            return (-65.0 + (indice % 10) * 2.0, -35.0 + (indice // 10) * 3.0)
    
    def _guardar_json(self, data: Dict, output_dir: str, filename: str) -> None:
        filepath = Path(output_dir) / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"Guardado: {filepath}")
    
    def _generar_csv(self, estadisticas: List[EstadisticasProvincia], config: Configuracion) -> None:
        rows = []
        for stats in estadisticas:
            if stats is None:
                continue
            
            row = {
                'provincia': stats.provincia,
                'area_total_km2': stats.area_km2,
                'total_pixels': stats.total_pixels
            }
            
            for class_name in config.class_info.values():
                class_data = stats.clasificaciones.get(class_name[0], {})
                row[f'{class_name[0]}_area_km2'] = class_data.get('area_km2', 0)
                row[f'{class_name[0]}_porcentaje'] = class_data.get('porcentaje', 0)
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        csv_path = Path(config.output_directory) / "estadisticas_provincias_real.csv"
        df.to_csv(csv_path, index=False)
        logging.info(f"CSV guardado: {csv_path}")
    
    def _generar_maximos(self, estadisticas: List[EstadisticasProvincia], config: Configuracion) -> None:
        maximos = {}
        
        for class_name, _ in config.class_info.values():
            max_porcentaje = 0
            provincia_max = None
            
            for stats in estadisticas:
                if stats is None:
                    continue
                
                class_data = stats.clasificaciones.get(class_name, {})
                porcentaje = class_data.get('porcentaje', 0)
                
                if porcentaje > max_porcentaje:
                    max_porcentaje = porcentaje
                    provincia_max = stats.provincia
            
            if provincia_max:
                maximos[class_name] = {
                    'provincia': provincia_max,
                    'porcentaje': round(max_porcentaje, 2),
                    'color': dict(config.class_info.values())[class_name]
                }
        
        self._guardar_json(maximos, config.output_directory, "maximos_por_clasificacion.json")

class AnalizadorProvincias:
    def __init__(self, config: Configuracion = None):
        self.config = config or Configuracion()
        self.lector = LectorShapefile(self.config)
        self.procesador = ProcesadorRasterio(self.config)
        self.generador = GeneradorJSON()
    
    def ejecutar_analisis(self) -> bool:
        try:
            logging.info("=" * 60)
            logging.info("ANÁLISIS DE PROVINCIAS")
            logging.info("=" * 60)
            
            if not self._verificar_archivos():
                return False
            
            provincias = self.lector.leer_provincias()
            if not provincias:
                logging.error("No se pudieron leer las provincias")
                return False
            
            logging.info(f"Se encontraron {len(provincias)} provincias")
            
            estadisticas = []
            for i, prov in enumerate(provincias):
                logging.info(f"Procesando {i+1}/{len(provincias)}: {prov.nombre}")
                stats = self.procesador.procesar_provincia(
                    self.config.raster_input, 
                    prov.geometry, 
                    prov.nombre
                )
                estadisticas.append(stats)
            
            estadisticas_validas = [s for s in estadisticas if s is not None]
            logging.info(f"Estadísticas válidas: {len(estadisticas_validas)}")
            
            self.generador.generar_salidas(estadisticas, self.config)
            
            logging.info("=" * 60)
            logging.info("ANÁLISIS COMPLETADO EXITOSAMENTE")
            logging.info("=" * 60)
            
            return True
            
        except Exception as e:
            logging.error(f"Error en análisis: {e}")
            return False
    
    def _verificar_archivos(self) -> bool:
        if not os.path.exists(self.config.raster_input):
            logging.error(f"Raster no encontrado: {self.config.raster_input}")
            return False
        
        if not os.path.exists(self.config.provincias_shapefile):
            logging.error(f"Shapefile no encontrado: {self.config.provincias_shapefile}")
            return False
        
        return True

def main():
    analizador = AnalizadorProvincias()
    exito = analizador.ejecutar_analisis()
    sys.exit(0 if exito else 1)

if __name__ == "__main__":
    main()

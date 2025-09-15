// Argentina
var roi = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
  .filter(ee.Filter.eq('country_na', 'Argentina'));

// Dynamic World para 2024
var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(roi)
  .filterDate('2024-01-01', '2024-12-31')
  .median()
  .select('label')
  .clip(roi);

// Parámetros
var dwVis = { min: 0, max: 8, palette: [
  '#419bdf', // Agua
  '#397d49', // Bosque
  '#88b053', // Matorrales
  '#7a87c6', // Pastizales
  '#e49635', // Tierras de Cultivo
  '#dfc35a', // Vegetación inundable
  '#c4281b', // Áreas urbanas
  '#a59b8f', // Suelo desnudo
  '#b39fe1'  // Nieve y hielo
]};


Map.centerObject(roi, 5);
Map.addLayer(dw, dwVis, 'Cobertura Terrestre DW 2024');

function addLegend() {
  var legend = ui.Panel({
    style: { position: 'bottom-left', padding: '8px 15px' }
  });

  var legendTitle = ui.Label({
    value: 'Clases de Cobertura Terrestre (DW 2024)',
    style: { fontWeight: 'bold', fontSize: '16px', margin: '0 0 4px 0' }
  });
  
  legend.add(legendTitle);

  var palette = dwVis.palette;
  var names = [
    'Agua', 'Bosque', 'Matorrales', 'Pastizales', 'Tierras de Cultivo',
    'Vegetación Inundable', 'Áreas Urbanas', 'Suelo Desnudo', 'Nieve y Hielo'
  ];

  for (var i = 0; i < names.length; i++) {
    var colorBox = ui.Label({ style: { backgroundColor: palette[i], padding: '8px', margin: '0 0 4px 0' } });
    var description = ui.Label({ value: names[i], style: { margin: '0 0 4px 6px' } });

    var legendItem = ui.Panel({ widgets: [colorBox, description], layout: ui.Panel.Layout.Flow('horizontal') });
    legend.add(legendItem);
  }

  Map.add(legend);
}

addLegend();

// Exportar la imagen 
Export.image.toDrive({
  image: dw,
  description: 'Cobertura_Terrestre_ARG_2024_DynamicWorld',
  scale: 10,
  region: roi.geometry(),
  maxPixels: 1e13
});

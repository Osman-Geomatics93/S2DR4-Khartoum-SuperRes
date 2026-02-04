/*
=============================================================================
Google Earth Engine Code Editor - Sentinel-2 Download for Khartoum, Sudan
=============================================================================

FIXED VERSION v3 - Fixed clip function issue

Instructions:
1. Go to https://code.earthengine.google.com
2. Copy and paste this entire script
3. Modify the CONFIGURATION section below
4. Click "Run"
5. Check the "Tasks" tab (top-right) to start exports
*/

// =============================================================================
// ⚠️ CONFIGURATION - MODIFY THESE VALUES
// =============================================================================

// Select location: 'khartoum_center', 'nile_confluence', 'omdurman', 'bahri', 'tuti_island'
var LOCATION = 'khartoum_center';

// Date range (dry season Nov-Apr has less clouds)
var START_DATE = '2024-01-01';
var END_DATE = '2024-02-28';

// Buffer around point in kilometers (2 = 4x4km area for S2DR4)
var BUFFER_KM = 2;

// Maximum cloud cover percentage
var MAX_CLOUD = 20;

// Google Drive folder for exports
var EXPORT_FOLDER = 'Khartoum_S2_Data';

// =============================================================================
// KHARTOUM LOCATIONS
// =============================================================================

var KHARTOUM_LOCATIONS = {
  'khartoum_center': {
    lon: 32.5599,
    lat: 15.5007,
    description: 'Khartoum City Center'
  },
  'nile_confluence': {
    lon: 32.5088,
    lat: 15.6177,
    description: 'Confluence of Blue and White Nile'
  },
  'omdurman': {
    lon: 32.4801,
    lat: 15.6445,
    description: 'Omdurman'
  },
  'bahri': {
    lon: 32.5521,
    lat: 15.6513,
    description: 'Khartoum North (Bahri)'
  },
  'tuti_island': {
    lon: 32.5167,
    lat: 15.6167,
    description: 'Tuti Island'
  },
  'greater_khartoum': {
    lon: 32.53,
    lat: 15.58,
    description: 'Greater Khartoum Area'
  }
};

// =============================================================================
// CREATE AREA OF INTEREST (AOI)
// =============================================================================

var loc = KHARTOUM_LOCATIONS[LOCATION];
var point = ee.Geometry.Point([loc.lon, loc.lat]);
var aoi = point.buffer(BUFFER_KM * 1000).bounds();

print('📍 Location: ' + loc.description);
print('📍 Coordinates: ' + loc.lon + ', ' + loc.lat);
print('📍 Area: ' + (BUFFER_KM * 2) + ' x ' + (BUFFER_KM * 2) + ' km');

// =============================================================================
// CLOUD MASKING FUNCTION
// =============================================================================

function maskS2Clouds(image) {
  var scl = image.select('SCL');
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10));
  return image.updateMask(mask).divide(10000);
}

// =============================================================================
// GET SENTINEL-2 COLLECTION
// =============================================================================

var collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(aoi)
    .filterDate(START_DATE, END_DATE)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', MAX_CLOUD))
    .sort('CLOUDY_PIXEL_PERCENTAGE');

// Print count
print('');
print('🔍 Images found:', collection.size());

// =============================================================================
// LIST AVAILABLE IMAGES
// =============================================================================

print('');
print('📋 Available Images (loading...)');

var imageInfo = collection.map(function(img) {
  return ee.Feature(null, {
    'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
    'cloud': img.get('CLOUDY_PIXEL_PERCENTAGE'),
    'tile': img.get('MGRS_TILE'),
    'id': img.get('PRODUCT_ID')
  });
});

imageInfo.evaluate(function(result) {
  if (result && result.features) {
    print('📋 Available Images (sorted by cloud cover):');
    var features = result.features;
    for (var i = 0; i < Math.min(features.length, 15); i++) {
      var props = features[i].properties;
      print('   ' + (i+1) + '. Date: ' + props.date + 
            ' | Cloud: ' + props.cloud.toFixed(2) + '%' +
            ' | Tile: ' + props.tile);
    }
  }
});

// =============================================================================
// SELECT BEST IMAGE AND PROCESS
// =============================================================================

// Get the best (least cloudy) image
var bestImage = ee.Image(collection.first());

// Clip first, then mask
var imageClipped = bestImage.clip(aoi);

// Apply cloud mask
var imageMasked = maskS2Clouds(imageClipped);

// Print best image info
bestImage.get('system:time_start').evaluate(function(timestamp) {
  if (timestamp) {
    var date = new Date(timestamp);
    print('');
    print('📸 Selected best image: ' + date.toISOString().split('T')[0]);
  }
});

bestImage.get('CLOUDY_PIXEL_PERCENTAGE').evaluate(function(cloud) {
  if (cloud !== null) {
    print('📸 Cloud cover: ' + cloud.toFixed(2) + '%');
  }
});

bestImage.get('MGRS_TILE').evaluate(function(tile) {
  if (tile) {
    print('📸 MGRS Tile: ' + tile);
  }
});

// =============================================================================
// VISUALIZATION
// =============================================================================

// Center map on AOI
Map.centerObject(aoi, 13);

// True Color
var visTrue = {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3};
Map.addLayer(imageMasked, visTrue, 'True Color (RGB)');

// False Color (Vegetation)
var visFalse = {bands: ['B8', 'B4', 'B3'], min: 0, max: 0.4};
Map.addLayer(imageMasked, visFalse, 'False Color (NIR-R-G)', false);

// NDVI
var ndvi = imageMasked.normalizedDifference(['B8', 'B4']).rename('NDVI');
var visNDVI = {min: -0.2, max: 0.8, palette: ['red', 'yellow', 'green', 'darkgreen']};
Map.addLayer(ndvi, visNDVI, 'NDVI', false);

// NDWI (Water)
var ndwi = imageMasked.normalizedDifference(['B3', 'B8']).rename('NDWI');
var visNDWI = {min: -0.5, max: 0.5, palette: ['brown', 'white', 'blue']};
Map.addLayer(ndwi, visNDWI, 'NDWI (Water)', false);

// Urban/Built-up
var visUrban = {bands: ['B12', 'B11', 'B4'], min: 0, max: 0.4};
Map.addLayer(imageMasked, visUrban, 'Urban (SWIR)', false);

// AOI Boundary
var empty = ee.Image().byte();
var aoiOutline = empty.paint({featureCollection: ee.FeatureCollection([ee.Feature(aoi)]), color: 1, width: 2});
Map.addLayer(aoiOutline, {palette: 'yellow'}, 'AOI Boundary');

// =============================================================================
// PREPARE BANDS FOR EXPORT
// =============================================================================

// 10 bands for S2DR4: B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12
var bands10 = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12'];
var image10Bands = imageMasked.select(bands10);

// RGB bands
var imageRGB = imageMasked.select(['B4', 'B3', 'B2']);

// Create filename prefix
var today = new Date();
var dateStr = today.toISOString().split('T')[0].replace(/-/g, '');
var filenamePrefix = 'S2_Khartoum_' + LOCATION + '_' + dateStr;

// =============================================================================
// EXPORT TO GOOGLE DRIVE
// =============================================================================

print('');
print('═══════════════════════════════════════════════════════════');
print('📤 EXPORT INSTRUCTIONS:');
print('═══════════════════════════════════════════════════════════');
print('   1. Click the "Tasks" tab (orange button, top-right)');
print('   2. Click "RUN" next to each export task');
print('   3. Confirm export settings in the popup');
print('   4. Wait for completion (progress shown in Tasks tab)');
print('   5. Files will appear in Google Drive: ' + EXPORT_FOLDER);
print('');

// Export 1: 10-band multispectral (for S2DR4)
Export.image.toDrive({
  image: image10Bands.toFloat(),
  description: filenamePrefix + '_10bands',
  folder: EXPORT_FOLDER,
  region: aoi,
  scale: 10,
  crs: 'EPSG:32636',
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF'
});

// Export 2: RGB True Color
Export.image.toDrive({
  image: imageRGB.toFloat(),
  description: filenamePrefix + '_RGB',
  folder: EXPORT_FOLDER,
  region: aoi,
  scale: 10,
  crs: 'EPSG:32636',
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF'
});

// Export 3: NDVI
Export.image.toDrive({
  image: ndvi.toFloat(),
  description: filenamePrefix + '_NDVI',
  folder: EXPORT_FOLDER,
  region: aoi,
  scale: 10,
  crs: 'EPSG:32636',
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF'
});

// Export 4: Full bands with SCL (unmasked for reference)
var imageFullClipped = imageClipped.select(['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12','SCL']).divide(10000);
Export.image.toDrive({
  image: imageFullClipped.toFloat(),
  description: filenamePrefix + '_FULL',
  folder: EXPORT_FOLDER,
  region: aoi,
  scale: 10,
  crs: 'EPSG:32636',
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF'
});

// =============================================================================
// SUMMARY
// =============================================================================

print('📁 Export tasks created:');
print('   1. ' + filenamePrefix + '_10bands.tif (for S2DR4)');
print('   2. ' + filenamePrefix + '_RGB.tif (True Color)');
print('   3. ' + filenamePrefix + '_NDVI.tif (Vegetation Index)');
print('   4. ' + filenamePrefix + '_FULL.tif (All bands + SCL)');
print('');
print('⚠️ IMPORTANT: Click "Tasks" tab and click RUN for each export!');
print('');
print('═══════════════════════════════════════════════════════════');
print('🔗 For S2DR4, use these settings:');
print('═══════════════════════════════════════════════════════════');
print('   lonlat = (' + loc.lon + ', ' + loc.lat + ')');
print('   date = "2024-01-07"  // Best date with 0% cloud');
print('');
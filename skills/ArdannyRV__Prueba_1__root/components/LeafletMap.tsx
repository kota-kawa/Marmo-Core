import { useState } from 'react';
import { View, Text, ActivityIndicator } from 'react-native';
import { WebView, WebViewMessageEvent } from 'react-native-webview';

interface LeafletMapProps {
  initialLocation?: { lat: number; lng: number };
  readOnly: boolean;
  onLocationSelect?: (latitude: number, longitude: number) => void;
  dishLocation?: { lat: number; lng: number };
  userLocation?: { lat: number; lng: number };
}

function generateMapHtml(
  lat: number,
  lng: number,
  readOnly: boolean,
  dishLocation?: { lat: number; lng: number } | null,
  userLocation?: { lat: number; lng: number } | null,
): string {
  const hasRoute = dishLocation != null && userLocation != null;

  let markerScript: string;
  if (hasRoute) {
    markerScript = `
    var dishMarker = L.marker([${dishLocation!.lat}, ${dishLocation!.lng}]).addTo(map);
    var userMarker = L.circleMarker([${userLocation!.lat}, ${userLocation!.lng}], {
      radius: 10,
      fillColor: "#4285F4",
      color: "#fff",
      weight: 3,
      opacity: 1,
      fillOpacity: 0.9
    }).addTo(map).bindPopup("Tú estás aquí").openPopup();
    var polyline = L.polyline([
      [${userLocation!.lat}, ${userLocation!.lng}],
      [${dishLocation!.lat}, ${dishLocation!.lng}]
    ], { color: 'red', weight: 4 }).addTo(map);
    var distKm = (L.latLng(${userLocation!.lat}, ${userLocation!.lng}).distanceTo(L.latLng(${dishLocation!.lat}, ${dishLocation!.lng})) / 1000).toFixed(2);
    polyline.bindTooltip(distKm + " km", {
      permanent: true,
      direction: 'center',
      className: 'distance-tooltip'
    }).openTooltip();
    map.fitBounds(polyline.getBounds(), { padding: [50, 50] });
    `;
  } else if (!readOnly) {
    markerScript = `
    var marker = L.marker([${lat}, ${lng}], { draggable: true }).addTo(map);
    map.on('click', function(e) {
      marker.setLatLng(e.latlng);
      sendPosition(e.latlng.lat, e.latlng.lng);
    });
    marker.on('dragend', function(e) {
      var pos = marker.getLatLng();
      sendPosition(pos.lat, pos.lng);
    });
    `;
  } else {
    markerScript = `
    var marker = L.marker([${lat}, ${lng}]).addTo(map);
    `;
  }

  return `<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { width: 100vw; height: 100vh; overflow: hidden; }
    #map { width: 100%; height: 100%; }
    .distance-tooltip {
      background: white !important;
      font-weight: bold !important;
      border-radius: 8px !important;
      padding: 5px 12px !important;
      font-size: 15px !important;
      border: 2px solid #E31837 !important;
      color: #333 !important;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2) !important;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', {
      center: [${lat}, ${lng}],
      zoom: 15,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    ${markerScript}

    function sendPosition(lat, lng) {
      if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
        window.ReactNativeWebView.postMessage(JSON.stringify({ latitude: lat, longitude: lng }));
      }
    }
  </script>
</body>
</html>`;
}

export default function LeafletMap({ initialLocation, readOnly, onLocationSelect, dishLocation, userLocation }: LeafletMapProps) {
  const [hasError, setHasError] = useState(false);
  const lat = initialLocation?.lat ?? -0.0022;
  const lng = initialLocation?.lng ?? -78.4459;
  const [html] = useState(() => generateMapHtml(lat, lng, readOnly, dishLocation, userLocation));

  const handleMessage = (event: WebViewMessageEvent) => {
    try {
      const { latitude, longitude } = JSON.parse(event.nativeEvent.data);
      if (onLocationSelect && typeof latitude === 'number' && typeof longitude === 'number') {
        onLocationSelect(latitude, longitude);
      }
    } catch {
      console.warn('LeafletMap: invalid message');
    }
  };

  if (hasError) {
    return (
      <View className="flex-1 items-center justify-center bg-gray-100 p-8">
        <Text className="text-gray-600 text-lg text-center mb-2">Error al cargar el mapa</Text>
        <Text className="text-gray-400 text-sm text-center">Verifica tu conexión a internet</Text>
      </View>
    );
  }

  return (
    <View className="flex-1">
      <WebView
        source={{ html }}
        style={{ flex: 1, backgroundColor: 'transparent' }}
        onMessage={handleMessage}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        startInLoadingState={true}
        renderLoading={() => (
          <View className="absolute inset-0 items-center justify-center bg-gray-100">
            <ActivityIndicator size="large" color="#E31837" />
            <Text className="mt-2 text-gray-600 text-sm">Cargando mapa...</Text>
          </View>
        )}
        onError={() => setHasError(true)}
      />
    </View>
  );
}

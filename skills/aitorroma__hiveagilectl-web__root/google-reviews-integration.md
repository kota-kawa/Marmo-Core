# Integración de Reseñas Reales de Google My Business

Este documento explica cómo configurar la integración con la API de Google Places para mostrar reseñas reales de Google My Business en tu sitio web.

## Requisitos Previos

1. **Cuenta de Google Cloud Platform**: Necesitarás crear una cuenta en [Google Cloud Platform](https://console.cloud.google.com/).
2. **Place ID de tu Negocio**: Identifica el Place ID de tu negocio usando la [herramienta de Google](https://developers.google.com/maps/documentation/javascript/examples/places-placeid-finder).
3. **Clave API de Google**: Tendrás que crear una clave API con acceso a la API de Places.

## Pasos para la Configuración

### 1. Crear un Proyecto en Google Cloud Platform

1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un nuevo proyecto o selecciona uno existente.
3. Anota el ID del proyecto, lo necesitarás más adelante.

### 2. Habilitar la API de Places

1. En el menú lateral, ve a "APIs y Servicios" > "Biblioteca".
2. Busca "Places API" y selecciónala.
3. Haz clic en "Habilitar".

### 3. Crear una Clave API

1. En el menú lateral, ve a "APIs y Servicios" > "Credenciales".
2. Haz clic en "Crear credenciales" y selecciona "Clave de API".
3. Se generará una nueva clave API. Cópiala y guárdala de forma segura.

### 4. Configurar Restricciones para la Clave API (Recomendado)

Para proteger tu clave API:

1. En la sección de credenciales, haz clic en tu clave API.
2. En "Restricciones de aplicación", selecciona "Sitios web HTTP referrer".
3. Añade los dominios donde se utilizará la clave (por ejemplo, `*.hiveagilectl.sh/*`).
4. En "Restricciones de API", selecciona "Places API".
5. Guarda los cambios.

### 5. Modificar el Código JavaScript

Edita el archivo `google-reviews.js` para usar tu clave API y Place ID:

```javascript
// Reemplaza estos valores con tus propias credenciales
const GOOGLE_API_KEY = 'TU_CLAVE_API_AQUÍ';
const PLACE_ID = 'TU_PLACE_ID_AQUÍ';

// Descomenta y modifica la función loadRealGoogleReviews para usar la API real
function loadRealGoogleReviews() {
    fetch(`https://cors-anywhere.herokuapp.com/https://maps.googleapis.com/maps/api/place/details/json?place_id=${PLACE_ID}&fields=reviews&key=${GOOGLE_API_KEY}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.result && data.result.reviews) {
            renderReviews(data.result.reviews);
        }
    })
    .catch(error => {
        console.error('Error al cargar reseñas de Google:', error);
    });
}
```

**Nota**: El uso de `cors-anywhere.herokuapp.com` es solo para desarrollo. En producción, deberías implementar tu propio proxy CORS o usar una solución del lado del servidor.

### 6. Solución Alternativa: Uso de un Proxy del Lado del Servidor

Para evitar exponer tu clave API en el código del cliente, considera implementar un endpoint del lado del servidor:

1. Crea un archivo PHP, Node.js o cualquier otro lenguaje de servidor que actúe como proxy.
2. Este endpoint hará la solicitud a la API de Google Places usando tu clave API.
3. Tu código JavaScript llamará a este endpoint en lugar de llamar directamente a la API de Google.

Ejemplo en PHP:

```php
<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$place_id = 'TU_PLACE_ID_AQUÍ';
$api_key = 'TU_CLAVE_API_AQUÍ';

$url = "https://maps.googleapis.com/maps/api/place/details/json?place_id={$place_id}&fields=reviews&key={$api_key}";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
$response = curl_exec($ch);
curl_close($ch);

echo $response;
?>
```

## Consideraciones Importantes

1. **Cuota de API**: La API de Places tiene límites de uso. Monitorea tu consumo en la consola de Google Cloud.
2. **Caché**: Considera almacenar en caché las reseñas para reducir el número de llamadas a la API.
3. **Términos de Servicio**: Asegúrate de cumplir con los [Términos de Servicio de Google](https://developers.google.com/maps/terms).
4. **Privacidad**: Informa a tus usuarios sobre el uso de datos de Google en tu sitio web.

## Recursos Adicionales

- [Documentación de la API de Places](https://developers.google.com/maps/documentation/places/web-service/overview)
- [Guía de Autenticación de Google](https://developers.google.com/maps/documentation/places/web-service/get-api-key)
- [Herramienta para encontrar Place ID](https://developers.google.com/maps/documentation/javascript/examples/places-placeid-finder)

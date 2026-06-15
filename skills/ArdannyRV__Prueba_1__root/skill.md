# Metodología de Ingeniería de Prompts (Prompt Engineering) - Gastro Map

## 1. Introducción
El desarrollo de la aplicación **Gastro Map** se ha construido sobre una arquitectura guiada rigurosamente por prompts específicos y detallados. Esta aproximación iterativa ha permitido eludir por completo el uso de diseños genéricos y decisiones arquitectónicas derivadas de plantillas por defecto. Cada funcionalidad y configuración ha sido forjada mediante la definición de un contexto inicial fuerte, garantizando soluciones a medida para las métricas del proyecto.

## 2. Identidad Corporativa (Bono 5pts)
Con el fin de garantizar una alta fidelidad visual e identidad de marca de alto perfil, se ejecutó una técnica directa de **"Instrucciones de Sistema"** para mantener absoluta consistencia con la herramienta gráfica Uniwind a lo largo de toda la UI. A través del prompting condicionado, se exigió la implementación estricta de códigos hexadecimales exactos representativos de Domino's Pizza en las configuraciones principales (`global.css`, abstracciones constantes en `theme.ts`):
- **Rojo Domino's**: `#E31837`
- **Azul Domino's**: `#0055A5`

El uso de esta metodología inyectada al sistema aseguró que cualquier clase utilitaria relacionada con colores respetase por contexto este patrón, automatizando la paleta de la aplicación sin riesgos de desviación.

## 3. Stack Tecnológico
La infraestructura técnica fue declarada y forzada en los prompts iniciales, logrando un ecosistema maduro que se acopla limpiamente. Este stack comprende:
- **Expo & TypeScript**: Eje central y robustez de tipado estático nativo.
- **Supabase Auth**: Sistema delegado para el modelado seguro de sesiones de usuario.
- **AsyncStorage**: Para el almacenamiento y persistencia offline liviana en dispositivo.
- **TanStack Query (React Query)**: Control y gestión de la sincronización de caché para un flujo asíncrono impecable.
- **Reanimated (v3)**: Motor fluidizado para procesamiento de animaciones en el UI Thread, evitando sobrecarga sobre puentes (bridges) de React Native.

## 4. Metodología de Prompts
El pipeline de generación se basó en segmentar en distintas ramas lógicas la inyección de prompts, atacando cada arista de Ingeniería de Software del proyecto de forma especializada:

- **Prompt de Arquitectura**: 
  Instruyó la creación de un andamiaje fuertemente tipado e impuso la estructura de carpetas funcional (`app/` para ruteo basado en Expo Router, `components/` para la presentación puramente visual desacoplada, y `hooks/` para abstracción de lógica reactiva de negocios).
- **Prompt de Estilos (Anti-Estilos Clásicos)**: 
  Definió una limitación terminante mediante *Instrucciones de Sistema*: la prohibición y eliminación total de llamadas a `StyleSheet.create`. Así se consolidó a su vez la adopción exclusiva del motor Tailwind v4 mediante Uniwind utilizando la propiedad declarativa `className`.
- **Prompt de Animaciones**: 
  Limitó el uso de animaciones a Reanimated 3 frente a Animated API y configuró comportamientos físicos hiper-precisos, exigiendo métodos encadenados como `FadeInDown.duration(800)` para la caída ralentizada y elegante de tarjetas, e integrando la implementación de gestores de interacciones (Swipe gestures a través de *React Native Gesture Handler*).
- **Prompt de Sensores (Automatización Automovilística UX)**: 
  Suministró la lógica de captura automática. Este prompt exigió reubicar la invocación de `getLastKnownPositionAsync` / `reverseGeocodeAsync` a fin de que ocurriera enteramente *under the hood* al interactuar con el submit de registro, enmascarando cualquier botón o control UI explícito para el GPS pero enviando de manera íntegra y transparente el dato al log interno de registro y base de datos local.

## 5. Conclusión
El conjunto final del software de *Gastro Map* representa una solución elaborada bajo demanda técnica. Las piezas arquitectónicas (Ruteo, Base de Datos Reactiva, Animaciones a 60 fps e iterativa y estricta aplicación de estilos semánticos vía Uniwind) no corresponden a una estructura base o "boilerplate" común, sino al direccionamiento conciso y proactivo proporcionado por una clara metodología de Prompt Engineering, entregando un producto robusto y fiel a los más altos estándares empresariales y técnicos estipulados.

import { useState } from 'react';
import { Alert, Image, ImageBackground, Modal, ScrollView, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useForm, Controller } from 'react-hook-form';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { useAuth } from '../../contexts/AuthContext';
import { useDishes } from '../../hooks/useDishes';
import { Dish } from '../../types/dish';
import { Colors } from '../../constants/theme';
import { AnimatedButton } from '../../components/AnimatedButton';
import LeafletMap from '../../components/LeafletMap';

interface AddForm {
  name: string;
  photo_uri: string | null;
  latitude: number | null;
  longitude: number | null;
  city: string | null;
  country: string | null;
}

export default function AddScreen() {
  const router = useRouter();
  const { session } = useAuth();
  const userId = session?.user?.id;
  const { addDishMutation } = useDishes(userId);

  const [pickingImage, setPickingImage] = useState(false);
  const [locating, setLocating] = useState(false);
  const [mapModalVisible, setMapModalVisible] = useState(false);
  const [confirmingLocation, setConfirmingLocation] = useState(false);

  const { control, handleSubmit, setValue, watch, getValues, reset, formState: { errors } } = useForm<AddForm>({
    defaultValues: {
      name: '',
      photo_uri: null,
      latitude: null,
      longitude: null,
      city: null,
      country: null,
    },
  });

  const photoUri = watch('photo_uri');
  const city = watch('city');
  const country = watch('country');
  const latitude = watch('latitude');
  const longitude = watch('longitude');

  const requestCameraPermission = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permiso requerido', 'Se necesita acceso a la cámara para tomar fotos.');
      return false;
    }
    return true;
  };

  const requestGalleryPermission = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permiso requerido', 'Se necesita acceso a la galería para seleccionar fotos.');
      return false;
    }
    return true;
  };

  const handleCamera = async () => {
    if (pickingImage) return;
    const ok = await requestCameraPermission();
    if (!ok) return;
    setPickingImage(true);
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        quality: 0.8,
      });
      if (!result.canceled && result.assets[0]) {
        setValue('photo_uri', result.assets[0].uri);
      }
    } finally {
      setPickingImage(false);
    }
  };

  const handleGallery = async () => {
    if (pickingImage) return;
    const ok = await requestGalleryPermission();
    if (!ok) return;
    setPickingImage(true);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        quality: 0.8,
      });
      if (!result.canceled && result.assets[0]) {
        setValue('photo_uri', result.assets[0].uri);
      }
    } finally {
      setPickingImage(false);
    }
  };

  const handleCurrentLocation = async () => {
    if (locating) return;
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permiso requerido', 'Se necesita acceso a la ubicación.');
      return;
    }

    setLocating(true);
    try {
      let pos = await Location.getLastKnownPositionAsync({});
      if (!pos) {
        pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Lowest });
      }
      if (!pos) {
        throw new Error('No se pudo obtener la ubicación.');
      }

      const geo = await Location.reverseGeocodeAsync({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
      });

      setValue('latitude', pos.coords.latitude);
      setValue('longitude', pos.coords.longitude);
      setValue('city', geo[0]?.city ?? null);
      setValue('country', geo[0]?.country ?? null);
    } catch (error: any) {
      Alert.alert('Error de GPS', error.message || 'No se pudo obtener la ubicación.');
    } finally {
      setLocating(false);
    }
  };

  const handleMapSelectLocation = (lat: number, lng: number) => {
    setValue('latitude', lat);
    setValue('longitude', lng);
  };

  const handleConfirmMapLocation = async () => {
    const [lat, lng] = getValues(['latitude', 'longitude']);
    if (lat == null || lng == null) return;

    setConfirmingLocation(true);
    try {
      const geo = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lng });
      setValue('city', geo[0]?.city ?? null);
      setValue('country', geo[0]?.country ?? null);
    } catch {
      // reverse geocode failed, proceed without city/country
    } finally {
      setConfirmingLocation(false);
      setMapModalVisible(false);
    }
  };

  const onSubmit = async (data: AddForm) => {
    if (!userId) return;
    if (!data.name || !data.photo_uri) {
      Alert.alert('Campos incompletos', 'Completa el nombre y la foto del plato.');
      return;
    }
    if (data.latitude == null || data.longitude == null) {
      Alert.alert('Ubicación requerida', 'Selecciona una ubicación para el plato.');
      return;
    }

    const dish: Dish = {
      id: Date.now().toString(),
      user_id: userId,
      name: data.name,
      photo_uri: data.photo_uri,
      city: data.city ?? '',
      country: data.country ?? '',
      latitude: data.latitude,
      longitude: data.longitude,
      created_at: new Date().toISOString(),
    };

    console.log('🚀 [NUEVO PLATO REGISTRADO]:', JSON.stringify(dish, null, 2));

    addDishMutation.mutate(dish, {
      onSuccess: () => {
        reset();
        router.replace('/');
      },
    });
  };

  return (
    <ImageBackground source={require('../../assets/images/mesa.jpg')} className="flex-1" resizeMode="cover">
      <View className="flex-1 bg-white/85">
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={{ padding: 24, flexGrow: 1 }}
        >
          <View className="bg-dominos-red pt-14 pb-6 px-4 rounded-b-3xl shadow-xl mb-6">
            <Text className="text-3xl font-black text-white text-center">Registrar Plato</Text>
          </View>

          <Controller
            control={control}
            name="name"
            rules={{ 
              required: 'El nombre es obligatorio',
              pattern: {
                value: /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/,
                message: 'El nombre solo puede contener letras y espacios'
              },
              validate: {
                noSoloEspacios: (value) => 
                  value.trim().length >= 3 || 'El nombre debe tener al menos 3 caracteres reales (no solo espacios)'
              }
            }}
            render={({ field: { onChange, onBlur, value } }) => (
              <>
                <Text className="text-sm font-semibold mb-1 text-gray-700">Nombre del plato</Text>
                <TextInput
                  className="border border-gray-300 rounded-lg p-3 mb-1 text-base bg-white"
                  placeholder="Ej: Pizza Pepperoni"
                  onBlur={onBlur}
                  onChangeText={onChange}
                  value={value}
                />
                {errors.name && <Text className="text-red-600 mb-2">{errors.name.message}</Text>}
              </>
            )}
          />

          <Text className="text-sm font-semibold mb-1 text-gray-700">Foto</Text>
          <View className="flex-row gap-3 mb-1">
            <TouchableOpacity
              className="flex-1 rounded-lg p-3 items-center"
              style={{ backgroundColor: Colors.dominosBlue }}
              onPress={handleCamera}
            >
              <Text className="text-white font-semibold">Cámara</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className="flex-1 rounded-lg p-3 items-center"
              style={{ backgroundColor: Colors.dominosBlue }}
              onPress={handleGallery}
            >
              <Text className="text-white font-semibold">Galería</Text>
            </TouchableOpacity>
          </View>
          {photoUri && (
            <Image source={{ uri: photoUri }} className="w-full h-48 rounded-lg mb-2" resizeMode="cover" />
          )}
          {pickingImage && <Text className="text-gray-500 text-center mb-2">Seleccionando imagen…</Text>}

          <Text className="text-sm font-semibold mb-1 text-gray-700 mt-4">Ubicación</Text>
          <View className="flex-row gap-3 mb-1">
            <TouchableOpacity
              className="flex-1 rounded-lg p-3 items-center"
              style={{ backgroundColor: Colors.dominosBlue }}
              onPress={handleCurrentLocation}
              disabled={locating}
            >
              <Text className="text-white font-semibold">
                {locating ? 'Obteniendo...' : 'Obtener ubicación actual'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              className="flex-1 rounded-lg p-3 items-center"
              style={{ backgroundColor: Colors.dominosBlue }}
              onPress={() => setMapModalVisible(true)}
            >
              <Text className="text-white font-semibold">Seleccionar en mapa</Text>
            </TouchableOpacity>
          </View>
          {latitude != null && longitude != null && (
            <View className="bg-green-50 border border-green-200 rounded-lg p-3 mb-1">
              <Text className="text-green-800 text-sm">✅ Ubicación seleccionada</Text>
              <Text className="text-green-600 text-xs mt-1">
                {latitude.toFixed(4)}, {longitude.toFixed(4)}
                {city || country ? ` — ${city ?? ''}${city && country ? ', ' : ''}${country ?? ''}` : ''}
              </Text>
            </View>
          )}

        </ScrollView>
        <View className="mb-6 items-center">
          <AnimatedButton
            title={addDishMutation.isPending ? 'Guardando...' : 'Registrar'}
            onPress={handleSubmit(onSubmit)}
            disabled={addDishMutation.isPending}
            className="w-2/3 self-center"
          />
        </View>
      </View>

      <Modal visible={mapModalVisible} animationType="slide" onRequestClose={() => setMapModalVisible(false)}>
        <View className="flex-1 bg-white">
          <View className="bg-dominos-red pt-12 pb-4 px-4 flex-row items-center justify-between">
            <Text className="text-white text-xl font-bold">Seleccionar ubicación</Text>
            <TouchableOpacity onPress={() => setMapModalVisible(false)}>
              <Text className="text-white text-lg">Cancelar</Text>
            </TouchableOpacity>
          </View>
          <View className="flex-1">
            <LeafletMap
              initialLocation={
                latitude != null && longitude != null
                  ? { lat: latitude, lng: longitude }
                  : undefined
              }
              readOnly={false}
              onLocationSelect={handleMapSelectLocation}
            />
          </View>
          <View className="p-4 bg-white border-t border-gray-200">
            <TouchableOpacity
              className="bg-dominos-red py-4 rounded-xl items-center"
              onPress={handleConfirmMapLocation}
              disabled={latitude == null || longitude == null || confirmingLocation}
            >
              <Text className="text-white font-bold text-lg">
                {confirmingLocation ? 'Obteniendo dirección...' : 'Confirmar ubicación'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </ImageBackground>
  );
}

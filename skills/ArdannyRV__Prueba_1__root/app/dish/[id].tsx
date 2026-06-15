import { useState } from 'react';
import { ActivityIndicator, Image, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { useDishes } from '../../hooks/useDishes';

export default function DishDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { session } = useAuth();
  const userId = session?.user?.id;
  const { dishesQuery } = useDishes(userId);
  const [imageLoaded, setImageLoaded] = useState(false);

  if (dishesQuery.isLoading) {
    return (
      <View className="flex-1 items-center justify-center bg-gray-100">
        <ActivityIndicator size="large" color="#E31837" />
      </View>
    );
  }

  const dishes = dishesQuery.data ?? [];
  const dish = dishes.find(d => d.id === id);

  if (!dish) {
    return (
      <View className="flex-1 items-center justify-center bg-gray-100 p-8">
        <Text className="text-gray-600 text-lg">Plato no encontrado</Text>
        <TouchableOpacity
          className="mt-4 bg-[#E31837] px-6 py-3 rounded-lg"
          onPress={() => router.back()}
        >
          <Text className="text-white font-semibold">Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-white">
      <View className="relative">
        <Image
          source={{ uri: dish.photo_uri }}
          className="w-full h-80"
          resizeMode="cover"
          onLoad={() => setImageLoaded(true)}
        />
        {!imageLoaded && (
          <View className="absolute inset-0 items-center justify-center bg-gray-200">
            <ActivityIndicator size="large" color="#E31837" />
          </View>
        )}
        <TouchableOpacity
          className="absolute top-12 left-4 bg-white/80 rounded-full p-2"
          onPress={() => router.back()}
        >
          <Text className="text-2xl">←</Text>
        </TouchableOpacity>
      </View>

      <ScrollView className="flex-1 px-6 pt-6">
        <Text className="text-3xl font-black text-gray-900 mb-2">{dish.name}</Text>

        {(dish.city || dish.country) && (
          <View className="flex-row items-center mb-2">
            <Text className="text-gray-500 text-base">📍 {dish.city}{dish.country ? `, ${dish.country}` : ''}</Text>
          </View>
        )}

        {dish.created_at && (
          <View className="flex-row items-center mb-6">
            <Text className="text-gray-500 text-base">
              📅 {new Date(dish.created_at).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </Text>
          </View>
        )}

        <TouchableOpacity
          className="bg-[#E31837] py-4 rounded-xl items-center mb-8 shadow-lg"
          onPress={() => router.push(`/map/${dish.id}`)}
        >
          <Text className="text-white font-bold text-lg">Ver ubicación</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

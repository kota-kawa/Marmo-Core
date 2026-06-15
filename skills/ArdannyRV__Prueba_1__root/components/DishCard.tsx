import { Image, Text, View } from 'react-native';
import { router } from 'expo-router';
import Animated, { FadeInDown, FadeOutLeft, runOnJS, useSharedValue } from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { Dish } from '../types/dish';
import { Colors } from '../constants/theme';

interface DishCardProps {
  dish: Dish;
  onDelete: (id: string) => void;
}

export function DishCard({ dish, onDelete }: DishCardProps) {
  const translateX = useSharedValue(0);

  const handlePress = () => {
    router.push(`/dish/${dish.id}`);
  };

  const panGesture = Gesture.Pan()
    .onUpdate((event) => {
      if (event.translationX < 0) {
        translateX.value = event.translationX;
      }
    })
    .onEnd((event) => {
      if (event.translationX < -100) {
        runOnJS(onDelete)(dish.id);
      }
      translateX.value = 0;
    });

  const tapGesture = Gesture.Tap().onEnd(() => {
    runOnJS(handlePress)();
  });

  const composedGesture = Gesture.Race(panGesture, tapGesture);
  const animatedStyle = { transform: [{ translateX }] };

  return (
    <GestureDetector gesture={composedGesture}>
      <Animated.View
        entering={FadeInDown.duration(4000)}
        exiting={FadeOutLeft}
        style={animatedStyle}
        className="bg-white rounded-xl mb-3 mx-4 shadow-sm border border-gray-200 overflow-hidden"
      >
        <View className="flex-row">
          <Image
            source={{ uri: dish.photo_uri }}
            className="w-24 h-24"
            resizeMode="cover"
          />
          <View className="flex-1 justify-center px-3">
            <Text className="text-lg font-bold" style={{ color: Colors.dominosRed }}>
              {dish.name}
            </Text>
            <Text className="text-sm text-gray-600 mt-1">
              {dish.city}{dish.country ? `, ${dish.country}` : ''}
            </Text>
            {dish.latitude != null && dish.longitude != null && (
              <Text className="text-[10px] text-gray-500 mt-1">
                lat: {dish.latitude}, long: {dish.longitude}
              </Text>
            )}
            {dish.created_at && (
              <Text className="text-[10px] text-gray-500 mt-1">
                {new Date(dish.created_at).toLocaleDateString()}
              </Text>
            )}
          </View>
        </View>
      </Animated.View>
    </GestureDetector>
  );
}

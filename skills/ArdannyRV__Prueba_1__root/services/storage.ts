import AsyncStorage from '@react-native-async-storage/async-storage';
import { Dish } from '../types/dish';

function storageKey(userId: string): string {
  return `@dishes_${userId}`;
}

export async function getDishes(userId: string): Promise<Dish[]> {
  try {
    const data = await AsyncStorage.getItem(storageKey(userId));
    if (!data) return [];
    return JSON.parse(data) as Dish[];
  } catch {
    return [];
  }
}

export async function saveDish(userId: string, dish: Dish): Promise<void> {
  const dishes = await getDishes(userId);
  dishes.unshift(dish);
  await AsyncStorage.setItem(storageKey(userId), JSON.stringify(dishes));
}

export async function deleteDish(userId: string, dishId: string): Promise<void> {
  const dishes = await getDishes(userId);
  const filtered = dishes.filter((d) => d.id !== dishId);
  await AsyncStorage.setItem(storageKey(userId), JSON.stringify(filtered));
}

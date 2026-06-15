import { FlatList, ImageBackground, Text, View } from 'react-native';
import { useAuth } from '../../contexts/AuthContext';
import { useDishes } from '../../hooks/useDishes';
import { DishCard } from '../../components/DishCard';
import { Colors } from '../../constants/theme';
import { AnimatedButton } from '../../components/AnimatedButton';
import { supabase } from '../../lib/supabase';

export default function HomeScreen() {
  const { session } = useAuth();
  const userId = session?.user?.id;
  const { dishesQuery, deleteDishMutation } = useDishes(userId);

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  if (dishesQuery.isLoading) {
    return (
      <View className="flex-1 bg-white justify-center items-center">
        <Text className="text-gray-500">Cargando…</Text>
      </View>
    );
  }

  return (
    <ImageBackground source={require('../../assets/images/mesa.jpg')} className="flex-1" resizeMode="cover">
      {dishesQuery.data?.length === 0 ? (
        <View className="flex-1 bg-white/85">
          <View className="bg-[#E31837] pt-14 pb-6 px-4 rounded-b-3xl shadow-xl mb-4">
            <Text className="text-4xl font-black text-white text-center">Platos</Text>
          </View>
          <View className="flex-1 justify-center items-center px-6">
            <Text className="text-2xl font-bold mb-2" style={{ color: Colors.dominosRed }}>
              Bienvenido
            </Text>
            <Text className="text-base text-gray-600 mb-8 text-center">
              Aún no has registrado ningún plato.
            </Text>
            <AnimatedButton
              title="Cerrar Sesión"
              onPress={handleLogout}
              className="bg-[#0055A5] p-2 w-2/3 self-center rounded-xl mb-6"
            />
          </View>
        </View>
      ) : (
        <View className="flex-1 bg-white/85">
          <View className="bg-[#E31837] pt-14 pb-6 px-4 rounded-b-3xl shadow-xl mb-4">
            <Text className="text-4xl font-black text-white text-center">Platos</Text>
          </View>
          <FlatList
            data={dishesQuery.data}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <DishCard
                dish={item}
                onDelete={(id) => deleteDishMutation.mutate(id)}
              />
            )}
            contentContainerClassName="pb-4"
            showsVerticalScrollIndicator={false}
            className="flex-1"
          />
          <View className="mb-6 items-center">
            <AnimatedButton
              title="Cerrar Sesión"
              onPress={handleLogout}
              className="bg-[#0055A5] p-2 w-2/3 self-center rounded-xl"
            />
          </View>
        </View>
      )}
    </ImageBackground>
  );
}

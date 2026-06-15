import { ImageBackground, View, Text, TextInput, TouchableOpacity, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useForm, Controller } from 'react-hook-form';
import { supabase } from '../../lib/supabase';

export default function RegisterScreen() {
  const router = useRouter();
  const { control, handleSubmit } = useForm({
    defaultValues: { email: '', password: '', confirmPassword: '' }
  });

  const onRegister = async (data: any) => {
    if (data.password !== data.confirmPassword) {
      alert("Las contraseñas no coinciden");
      return;
    }
    const { error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
    });
    if (error) alert(error.message);
    else alert("¡Registro exitoso! Revisa tu correo.");
  };

  return (
    <ImageBackground 
      source={require('../../assets/images/mesa_login_registro.jpg')} 
      className="flex-1" 
      resizeMode="cover"
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} className="bg-black/40">
        <View className="flex-1 justify-center p-8">
          {/* Título solo en blanco */}
          <Text className="text-4xl font-black text-white text-center mb-12">
            Crear Cuenta
          </Text>
          
          <Controller
            control={control}
            name="email"
            render={({ field: { onChange, value } }) => (
              <TextInput
                className="bg-white/90 p-4 rounded-xl mb-4 text-base"
                placeholder="Correo electrónico"
                placeholderTextColor="#666"
                onChangeText={onChange}
                value={value}
              />
            )}
          />

          <Controller
            control={control}
            name="password"
            render={({ field: { onChange, value } }) => (
              <TextInput
                className="bg-white/90 p-4 rounded-xl mb-4 text-base"
                placeholder="Contraseña"
                placeholderTextColor="#666"
                secureTextEntry
                onChangeText={onChange}
                value={value}
              />
            )}
          />

          <Controller
            control={control}
            name="confirmPassword"
            render={({ field: { onChange, value } }) => (
              <TextInput
                className="bg-white/90 p-4 rounded-xl mb-8 text-base"
                placeholder="Confirmar contraseña"
                placeholderTextColor="#666"
                secureTextEntry
                onChangeText={onChange}
                value={value}
              />
            )}
          />

          {/* Botón de Registro en Rojo Domino's para destacar la acción principal */}
          <TouchableOpacity 
            className="bg-[#E31837] p-4 rounded-xl items-center mb-6 shadow-lg"
            onPress={handleSubmit(onRegister)}
          >
            <Text className="text-white font-bold text-lg">Registrarse</Text>
          </TouchableOpacity>

          {/* Enlace solo texto blanco */}
          <TouchableOpacity onPress={() => router.back()}>
            <Text className="text-white text-center font-semibold text-base">
              Ya tengo cuenta, ir al Login
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </ImageBackground>
  );
}
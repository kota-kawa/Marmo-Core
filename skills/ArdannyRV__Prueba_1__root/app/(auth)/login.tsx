import { ImageBackground, View, Text, TextInput, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useForm, Controller } from 'react-hook-form';
import { supabase } from '../../lib/supabase';

export default function LoginScreen() {
  const router = useRouter();
  const { control, handleSubmit } = useForm({
    defaultValues: { email: '', password: '' }
  });

  const onLogin = async (data: any) => {
    const { error } = await supabase.auth.signInWithPassword(data);
    if (error) alert(error.message);
  };

  return (
    <ImageBackground 
      source={require('../../assets/images/mesa_login_registro.jpg')} 
      className="flex-1" 
      resizeMode="cover"
    >
      <View className="flex-1 bg-black/40 justify-center p-8">
        {/* Título solo en blanco, sin fondo rojo */}
        <Text className="text-5xl font-black text-white text-center mb-12">
          Gastro Map
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
              className="bg-white/90 p-4 rounded-xl mb-8 text-base"
              placeholder="Contraseña"
              placeholderTextColor="#666"
              secureTextEntry
              onChangeText={onChange}
              value={value}
            />
          )}
        />

        {/* Botón de acción en azul */}
        <TouchableOpacity 
          className="bg-[#0055A5] p-4 rounded-xl items-center mb-6 shadow-lg"
          onPress={handleSubmit(onLogin)}
        >
          <Text className="text-white font-bold text-lg">Entrar</Text>
        </TouchableOpacity>

        {/* Enlace sin fondo azul, solo texto blanco */}
        <TouchableOpacity onPress={() => router.push('/register')}>
          <Text className="text-white text-center font-semibold text-base">
            ¿No tienes cuenta? Regístrate aquí
          </Text>
        </TouchableOpacity>
      </View>
    </ImageBackground>
  );
}
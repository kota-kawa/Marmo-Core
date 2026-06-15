import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Dish } from '../types/dish';
import { getDishes, saveDish, deleteDish } from '../services/storage';

export function useDishes(userId: string | undefined) {
  const queryClient = useQueryClient();

  const dishesQuery = useQuery({
    queryKey: ['dishes', userId],
    queryFn: () => getDishes(userId!),
    enabled: !!userId,
  });

  const addDishMutation = useMutation({
    mutationFn: (dish: Dish) => saveDish(userId!, dish),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dishes', userId] });
    },
  });

  const deleteDishMutation = useMutation({
    mutationFn: (dishId: string) => deleteDish(userId!, dishId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dishes', userId] });
    },
  });

  return { dishesQuery, addDishMutation, deleteDishMutation };
}

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { getFavorites, addFavorite, removeFavorite } from 'src/api/favorites';
import { useAuthStore } from './auth';

export const useFavoritesStore = defineStore('favorites', () => {
  const auth = useAuthStore();

  const favorites = ref<Set<number>>(new Set());

  async function loadFavorites() {
    if (!auth.user) return;

    const res = await getFavorites(auth.user.id);

    favorites.value = new Set(res.results.map((t) => t.id));
  }

  function isFavorite(id: number) {
    return favorites.value.has(id);
  }

  async function toggleFavorite(id: number) {
    if (!auth.user) return;

    if (favorites.value.has(id)) {
      await removeFavorite(auth.user.id, id);
      favorites.value.delete(id);
    } else {
      await addFavorite(auth.user.id, id);
      favorites.value.add(id);
    }
  }

  return {
    favorites,
    loadFavorites,
    isFavorite,
    toggleFavorite,
  };
});

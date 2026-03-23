<template>
  <q-layout view="hHh lpR fFf" class="custom-lightgrey-background">
    <AppHeader />
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import AppHeader from 'components/AppHeader.vue';
import { onMounted } from 'vue';
import { useAuthStore } from 'src/stores/auth';
import { useFavoritesStore } from 'src/stores/favorites';

const auth = useAuthStore();
const favorites = useFavoritesStore();

onMounted(() => {
  void auth.fetchUser();
  void favorites.loadFavorites();
});
</script>

<template>
  <div class="column full-height">
    <q-card v-if="props.tours.length === 0" class="border-radius-md full-height">
      <q-card-section class="text-center full-height column justify-center">
        <div>
          <q-icon name="search_off" size="48px" color="primary" />
        </div>
        <div class="custom-font-size text-primary q-mb-xs">
          {{ emptyStateTitle }}
        </div>
        <div class="text-primary custom-opacity" style="font-size: 16px">
          {{ emptyStateSubtitle }}
        </div>
      </q-card-section>
    </q-card>

    <template v-else>
      <TourCard
        v-for="tour in props.tours"
        :key="tour.id"
        :tour="tour"
        :isFavorite="favorites.isFavorite(tour.id)"
        class="tour-card-item"
        @toggle-favorite="favorites.toggleFavorite"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import TourCard from './TourCard.vue';
import { useFavoritesStore } from 'src/stores/favorites';
import type { Tour } from 'src/api/filters';

const props = defineProps<{
  tours: Tour[];
  loading?: boolean;
  hasSearched?: boolean;
}>();

const favorites = useFavoritesStore();

const emptyStateTitle = computed(() => {
  return props.hasSearched ? 'К сожалению, ничего не найдено' : 'Начните поиск туров';
});

const emptyStateSubtitle = computed(() => {
  return props.hasSearched
    ? 'Попробуйте изменить параметры поиска или фильтры'
    : 'Заполните форму поиска выше, чтобы найти подходящие туры';
});
</script>

<style scoped>
.tour-card-item:first-child {
  border-top-left-radius: 20px !important;
  border-top-right-radius: 20px !important;
}

.tour-card-item:last-child {
  border-bottom-left-radius: 20px !important;
  border-bottom-right-radius: 20px !important;
}
</style>

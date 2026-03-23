<template>
  <div class="column full-height">
    <q-card v-if="props.tours.length === 0" square class="full-height empty-list">
      <q-card-section class="text-center full-height column justify-center">
        <div class="custom-font-size text-primary">
          {{ emptyStateTitle }}
        </div>
      </q-card-section>
    </q-card>

    <template v-else>
      <TourCard
        v-for="tour in props.tours"
        :key="tour.id"
        :tour="tour"
        :isFavorite="true"
        @toggle-favorite="handleToggleFavorite"
        class="tour-card-item"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import TourCard from '../home/TourCard.vue';
import type { FavoriteTour } from 'src/api/favorites';

const props = defineProps<{
  tours: FavoriteTour[];
  hasSearched?: boolean;
}>();

const emit = defineEmits<{
  (e: 'toggle-favorite', tourId: number): void;
}>();

const emptyStateTitle = computed(() => {
  return props.hasSearched
    ? 'В избранном нет туров с выбранными фильтрами'
    : 'Вы ещё ничего не добавляли в избранное';
});

function handleToggleFavorite(tourId: number) {
  emit('toggle-favorite', tourId);
}
</script>

<style scoped>
.tour-card-item:last-child {
  border-bottom-right-radius: 20px !important;
}

.empty-list {
  border-bottom-right-radius: 20px !important;
}

@media (max-width: 1023px) {
  .tour-card-item:last-child {
    border-bottom-left-radius: 20px !important;
  }
  .empty-list {
    border-bottom-left-radius: 20px !important;
  }
}
</style>

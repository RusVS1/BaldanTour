<template>
  <q-page class="q-pa-lg">
    <div class="row">
      <q-card
        square
        class="col-12 q-pa-md"
        style="border-top-left-radius: 20px !important; border-top-right-radius: 20px !important"
      >
        <div class="row items-center">
          <div class="text-primary" style="font-size: 32px">Избранное</div>
          <q-icon name="favorite" size="40px" class="q-ml-sm" style="color: #dd5555" />
        </div>
      </q-card>
    </div>

    <div class="row items-stretch">
      <div class="col-12 col-md-3">
        <FiltersSidebar
          mode="favorites"
          square
          class="filters-sidebar"
          @filter-change="handleFilterChange"
        />
      </div>
      <div class="col-12 col-md-9">
        <FavoriteToursList
          :tours="displayedTours"
          :has-searched="hasSearched"
          class="favorite-tours-list extra-margin"
          @toggle-favorite="handleToggleFavorite"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import FiltersSidebar from 'components/home/FiltersSidebar.vue';
import FavoriteToursList from 'components/favorite/FavoriteToursList.vue';
import { getFavorites, removeFavorite } from 'src/api/favorites';
import { useAuthStore } from 'src/stores/auth';
import type { FavoriteTour } from 'src/api/favorites';
import type { FilterParams } from 'src/api/filters';

const auth = useAuthStore();
const tours = ref<FavoriteTour[]>([]);
const hasSearched = ref(false);
const currentFilters = ref<FilterParams>({});

const displayedTours = computed(() => {
  let result = [...tours.value];

  if (currentFilters.value.priceFrom != null) {
    result = result.filter((t) => t.price_per_person >= currentFilters.value.priceFrom!);
  }
  if (currentFilters.value.priceTo != null) {
    result = result.filter((t) => t.price_per_person <= currentFilters.value.priceTo!);
  }

  if (currentFilters.value.type) {
    result = result.filter((t) => t.meta?.rest_type === currentFilters.value.type);
  }

  if (currentFilters.value.hotelType) {
    result = result.filter((t) => t.meta?.hotel_type === currentFilters.value.hotelType);
  }

  if (currentFilters.value.category != null) {
    result = result.filter(
      (t) => String(t.meta?.hotel_category) === String(currentFilters.value.category),
    );
  }

  if (currentFilters.value.food) {
    result = result.filter((t) => t.meta?.meal === currentFilters.value.food);
  }

  if (currentFilters.value.sort) {
    result.sort((a, b) => {
      switch (currentFilters.value.sort) {
        case 'price_asc':
          return a.price_per_person - b.price_per_person;
        case 'price_desc':
          return b.price_per_person - a.price_per_person;
        case 'hotel_category':
          return (Number(b.meta?.hotel_category) || 0) - (Number(a.meta?.hotel_category) || 0);
        default:
          return 0;
      }
    });
  }

  return result;
});

async function loadFavorites() {
  if (!auth.user) return;
  const res = await getFavorites(auth.user.id);
  tours.value = res.results;
}

function handleFilterChange(newFilters: FilterParams) {
  currentFilters.value = newFilters;
  hasSearched.value = true;
}

async function handleToggleFavorite(tourId: number) {
  if (!auth.user) return;
  await removeFavorite(auth.user.id, tourId);
  await loadFavorites();
}

onMounted(loadFavorites);
</script>

<style scoped>
.filters-sidebar {
  height: 100%;
  border-bottom-left-radius: 20px !important;
}

.extra-margin {
  margin-left: 1px;
}

@media (max-width: 1023px) {
  .filters-sidebar {
    border-bottom-left-radius: 0 !important;
  }
  .extra-margin {
    margin-left: 0;
  }
}
</style>

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
        <FiltersSidebar square class="filters-sidebar" />
      </div>
      <div class="col-12 col-md-9">
        <FavoriteToursList class="favorite-tours-list" />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import FiltersSidebar from 'components/home/FiltersSidebar.vue';
import FavoriteToursList from 'components/favorite/FavoriteToursList.vue';
</script>

<style scoped>
.filters-sidebar {
  height: 100%;
  border-bottom-left-radius: 20px !important;
}

@media (max-width: 1023px) {
  .filters-sidebar {
    border-bottom-left-radius: 0 !important;
  }
}
</style>

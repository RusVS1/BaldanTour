<template>
  <q-page class="q-pa-lg">
    <div class="row justify-center">
      <SearchBar class="q-mb-md border-radius-md col-12 col-md-10" />
    </div>
    <div class="row q-col-gutter-lg">
      <div class="col-12 col-md-3">
        <FiltersSidebar class="border-radius-md" style="position: sticky; top: 90px" />
      </div>
      <div class="col-12 col-md-9">
        <ToursList />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import SearchBar from 'components/home/SearchBar.vue';
import FiltersSidebar from 'components/home/FiltersSidebar.vue';
import ToursList from 'components/home/ToursList.vue';
</script>

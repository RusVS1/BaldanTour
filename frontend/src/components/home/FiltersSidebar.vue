<template>
  <q-card class="q-pa-lg">
    <div class="custom-font-size text-weight-medium text-primary text-center">Фильтры</div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Тип отдыха</div>
      <q-select
        v-model="filters.type"
        :options="options"
        options-dense
        outlined
        dense
        clearable
        use-input
        fill-input
        hide-selected
        color="primary"
        options-selected-class="custom-font-size text-primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
      />
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Цена</div>

      <div class="row q-col-gutter-sm">
        <div class="col">
          <q-input
            v-model="filters.priceFrom"
            type="number"
            outlined
            dense
            placeholder="от"
            input-class="custom-font-size text-primary"
            dropdown-icon="keyboard_double_arrow_down"
            class="custom-arrow-blue"
          />
        </div>
        <div class="col">
          <q-input
            v-model="filters.priceTo"
            type="number"
            outlined
            dense
            placeholder="до"
            input-class="custom-font-size text-primary"
            dropdown-icon="keyboard_double_arrow_down"
            class="custom-arrow-blue"
          />
        </div>
      </div>
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Тип отеля</div>
      <q-select
        v-model="filters.hotelType"
        :options="options"
        options-dense
        outlined
        dense
        clearable
        use-input
        fill-input
        hide-selected
        color="primary"
        options-selected-class="custom-font-size text-primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
      />
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Категория отеля</div>
      <q-select
        v-model="filters.category"
        :options="options"
        options-dense
        outlined
        dense
        clearable
        use-input
        fill-input
        hide-selected
        color="primary"
        options-selected-class="custom-font-size text-primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
      />
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Тип питания</div>
      <q-select
        v-model="filters.food"
        :options="options"
        options-dense
        outlined
        dense
        clearable
        use-input
        fill-input
        hide-selected
        color="primary"
        options-selected-class="custom-font-size text-primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
      />
    </div>

    <div>
      <div class="custom-font-size text-primary q-mb-xs">Сортировать по</div>
      <q-select
        v-model="filters.sort"
        :options="options"
        options-dense
        outlined
        dense
        clearable
        use-input
        fill-input
        hide-selected
        color="primary"
        options-selected-class="custom-font-size text-primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
      />
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { reactive } from 'vue';

const filters = reactive({
  type: null as string | null,
  priceFrom: null as number | null,
  priceTo: null as number | null,
  hotelType: null as string | null,
  category: null as string | null,
  food: null as string | null,
  sort: null as string | null,
});

const options = ['Вариант 1', 'Вариант 2', 'Вариант 3'];
</script>

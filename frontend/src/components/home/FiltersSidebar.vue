<template>
  <q-card class="q-pa-lg">
    <div class="custom-font-size text-weight-medium text-primary text-center q-mb-md">Фильтры</div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Тип отдыха</div>
      <q-select
        v-model="filters.type"
        :options="options.restType"
        option-label="label"
        option-value="value"
        options-dense
        outlined
        emit-value
        map-options
        dense
        clearable
        color="primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
        @update:model-value="emitFilters"
      />
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Цена</div>
      <div class="row q-col-gutter-sm">
        <div class="col">
          <q-input
            v-model.number="filters.priceFrom"
            type="number"
            outlined
            dense
            placeholder="от"
            input-class="custom-font-size text-primary"
            class="custom-arrow-blue"
            @blur="emitFilters"
          />
        </div>
        <div class="col">
          <q-input
            v-model.number="filters.priceTo"
            type="number"
            outlined
            dense
            placeholder="до"
            input-class="custom-font-size text-primary"
            class="custom-arrow-blue"
            @blur="emitFilters"
          />
        </div>
      </div>
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Тип отеля</div>
      <q-select
        v-model="filters.hotelType"
        :options="options.hotelType"
        option-label="label"
        option-value="value"
        options-dense
        outlined
        emit-value
        map-options
        dense
        clearable
        color="primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
        @update:model-value="emitFilters"
      />
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Категория отеля</div>
      <q-select
        v-model="filters.category"
        :options="options.hotelCategory"
        option-label="label"
        option-value="value"
        options-dense
        outlined
        emit-value
        map-options
        dense
        clearable
        color="primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
        @update:model-value="emitFilters"
      />
    </div>

    <div class="q-mb-sm">
      <div class="custom-font-size text-primary q-mb-xs">Тип питания</div>
      <q-select
        v-model="filters.food"
        :options="options.meal"
        option-label="label"
        option-value="value"
        options-dense
        outlined
        emit-value
        map-options
        dense
        clearable
        color="primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
        @update:model-value="emitFilters"
      />
    </div>

    <div>
      <div class="custom-font-size text-primary q-mb-xs">Сортировать по</div>
      <q-select
        v-model="filters.sort"
        :options="sortOptions"
        option-label="label"
        option-value="value"
        options-dense
        outlined
        emit-value
        map-options
        dense
        clearable
        color="primary"
        input-class="custom-font-size text-primary"
        popup-content-class="custom-font-size text-primary"
        dropdown-icon="keyboard_double_arrow_down"
        class="custom-arrow-blue"
        @update:model-value="emitFilters"
      />
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import {
  getFilterOptions,
  formatOptions,
  type FilterOption,
  type FilterParams,
} from 'src/api/filters';
import { getFavoriteFilters } from 'src/api/favorites';
import { useAuthStore } from 'src/stores/auth';

const auth = useAuthStore();

const props = defineProps<{
  mode?: 'search' | 'favorites';
}>();

type Filters = FilterParams & {
  priceFrom?: number | null;
  priceTo?: number | null;
};

const filters = ref<Filters>({
  type: null,
  priceFrom: null,
  priceTo: null,
  hotelType: null,
  category: null,
  food: null,
  sort: null,
});

const options = ref({
  restType: [] as FilterOption[],
  hotelType: [] as FilterOption[],
  hotelCategory: [] as FilterOption[],
  meal: [] as FilterOption[],
});

const sortOptions: FilterOption[] = [
  { label: 'Сначала дешёвые', value: 'price_asc' },
  { label: 'Сначала дорогие', value: 'price_desc' },
  { label: 'По категории отеля', value: 'hotel_category' },
  { label: 'По типу отеля', value: 'hotel_type' },
  { label: 'По типу отдыха', value: 'rest_type' },
  { label: 'По типу питания', value: 'meal' },
];

const emit = defineEmits<{
  (e: 'filter-change', filters: Partial<Filters>): void;
}>();

let emitTimeout: ReturnType<typeof setTimeout> | null = null;

function emitFilters() {
  if (emitTimeout) clearTimeout(emitTimeout);

  emitTimeout = setTimeout(() => {
    const activeFilters = Object.fromEntries(
      Object.entries(filters.value).filter(([, value]) => {
        if (value === null || value === undefined || value === '') return false;
        if (typeof value === 'number' && Number.isNaN(value)) return false;
        return true;
      }),
    ) as Partial<Filters>;

    emit('filter-change', activeFilters);
  }, 300);
}

watch(
  () => filters.value,
  () => emitFilters(),
  { deep: true },
);

onMounted(async () => {
  try {
    let restType, hotelType, hotelCategory, meal;

    if (props.mode === 'favorites' && auth.user) {
      const [rt, ht, hc, m] = await Promise.all([
        getFavoriteFilters.restType(auth.user.id),
        getFavoriteFilters.hotelType(auth.user.id),
        getFavoriteFilters.hotelCategory(auth.user.id),
        getFavoriteFilters.meal(auth.user.id),
      ]);
      restType = rt;
      hotelType = ht;
      hotelCategory = hc;
      meal = m;
    } else {
      const [rt, ht, hc, m] = await Promise.all([
        getFilterOptions.restType(),
        getFilterOptions.hotelType(),
        getFilterOptions.hotelCategory(),
        getFilterOptions.meal(),
      ]);
      restType = rt;
      hotelType = ht;
      hotelCategory = hc;
      meal = m;
    }

    options.value.restType = formatOptions(restType.values);
    options.value.hotelType = formatOptions(hotelType.values);
    options.value.hotelCategory = formatOptions(
      hotelCategory.values.map((v) => ({ label: String(v), value: v })),
    );
    options.value.meal = formatOptions(meal.values);
  } catch (e) {
    console.error('Ошибка при загрузке опций', e);
  }
});

function resetFilters() {
  filters.value = {
    type: null,
    priceFrom: null,
    priceTo: null,
    hotelType: null,
    category: null,
    food: null,
    sort: null,
  };
}

defineExpose({ resetFilters });
</script>

<style scoped>
:deep(.q-field__native) {
  color: var(--q-primary) !important;
  font-size: 20px;
}
</style>

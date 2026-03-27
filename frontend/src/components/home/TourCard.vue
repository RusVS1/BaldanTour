<template>
  <q-card square class="row q-pa-md no-wrap">
    <div class="col-auto image-col">
      <q-img :src="imageSrc" class="border-radius-md tour-image" />
    </div>

    <div class="col-auto q-pl-lg">
      <div class="text-primary text-weight-bold q-mb-xs title-text">
        {{ tour.hotel_name }}
        <span v-if="tour.meta.hotel_category"
          >{{ tour.meta.hotel_category }}<span style="vertical-align: super">⭑</span></span
        >
      </div>

      <div class="text-primary custom-opacity custom-font-size q-mb-xs location-text">
        {{ tour.meta.country_slug }}
      </div>

      <div class="text-primary custom-opacity custom-font-size q-mb-xs hotel-text">
        {{ tour.meta.hotel_type }}
        <span v-if="tour.hotel_rating">, {{ tour.hotel_rating }}</span>
      </div>

      <div
        v-if="tour.meta.meal"
        class="text-primary custom-opacity custom-font-size q-mb-sm food-text"
      >
        {{ tour.meta.meal }}
      </div>
    </div>

    <div class="col text-center description-col">
      <div class="text-primary custom-font-size ellipsis-3-lines description-text">
        {{ tour.answer_description }}
      </div>
    </div>

    <div class="col-auto q-pr-md text-right actions-col">
      <div class="q-mb-md price-text">{{ tour.price_per_person }} ₽ за человека</div>

      <div class="q-mt-lg row items-center q-gutter-md justify-end">
        <q-icon
          :name="isFavorite ? 'favorite' : 'favorite_border'"
          :color="isFavorite ? '' : 'primary'"
          :style="isFavorite ? { color: '#dd5555' } : {}"
          class="cursor-pointer heart-icon"
          @click="toggleFavorite"
        />

        <q-btn
          label="Перейти"
          color="light-blue"
          rounded
          unelevated
          no-caps
          class="text-white go-btn"
          @click="openTourLink"
        />
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import type { TourBase } from 'src/api/filters';

const props = defineProps<{
  tour: TourBase;
  isFavorite?: boolean;
}>();

const emit = defineEmits<{
  (e: 'toggle-favorite', tourId: number): void;
}>();

const isFavorite = ref(props.isFavorite ?? false);

watch(
  () => props.isFavorite,
  (val) => {
    isFavorite.value = !!val;
  },
);

function toggleFavorite() {
  isFavorite.value = !isFavorite.value;
  emit('toggle-favorite', props.tour.id);
}

function openTourLink() {
  if (props.tour.buy_link) {
    window.open(props.tour.buy_link, '_blank', 'noopener,noreferrer');
  }
}

import placeholder from '../../images/tour-placeholder.jpg';

const imageSrc = computed(() => {
  return props.tour.main_image_url || placeholder;
});
</script>

<style scoped>
.title-text {
  font-size: 24px;
}
.location-text,
.hotel-text,
.food-text,
.description-text {
  font-size: 20px;
}
.price-text {
  color: #c50000;
  font-size: 24px;
}
.go-btn {
  min-width: 190px;
  height: 52px;
  font-size: 24px;
}
.heart-icon {
  font-size: 48px;
}
.tour-image {
  width: 176px;
  height: 150px;
}

@media (min-width: 1024px) and (max-width: 1440px) {
  .tour-image {
    width: 140px;
    height: 120px;
  }
  .title-text {
    font-size: 20px;
  }
  .location-text,
  .hotel-text,
  .food-text,
  .description-text {
    font-size: 16px;
  }
  .price-text {
    font-size: 20px;
  }
  .go-btn {
    min-width: 130px;
    height: 42px;
    font-size: 16px;
  }
  .heart-icon {
    font-size: 32px;
  }
}
</style>

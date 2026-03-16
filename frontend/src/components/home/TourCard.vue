<template>
  <q-card square class="row q-pa-md no-wrap">
    <div class="col-auto image-col">
      <q-img src="https://picsum.photos/200/150" class="border-radius-md tour-image" />
    </div>

    <div class="col-auto q-pl-lg">
      <div class="text-primary text-weight-bold q-mb-xs title-text">
        {{ tour.title }}
      </div>

      <div class="text-primary custom-opacity custom-font-size q-mb-xs location-text">
        {{ tour.location }}
      </div>

      <div class="text-primary custom-opacity custom-font-size q-mb-xs hotel-text">
        {{ tour.hotel_name }}, {{ tour.hotel_type }}, {{ tour.hotel_rating }}
      </div>

      <div class="text-primary custom-opacity custom-font-size q-mb-sm food-text">
        {{ tour.food_type }}
      </div>
    </div>

    <div class="col text-center description-col">
      <div class="text-primary custom-font-size ellipsis-3-lines description-text">
        {{ tour.description }}
      </div>
    </div>

    <div class="col-auto q-pr-md text-right actions-col">
      <div class="q-mb-md price-text">{{ tour.price }} ₽</div>

      <div class="q-mt-lg row items-center q-gutter-md justify-end">
        <q-icon
          :name="isFavorite ? 'favorite' : 'favorite_border'"
          :color="isFavorite ? '' : 'primary'"
          :style="isFavorite ? { color: '#C50000' } : {}"
          class="cursor-pointer heart-icon"
          @click="isFavorite = !isFavorite"
        />

        <q-btn
          label="Перейти"
          color="light-blue"
          rounded
          unelevated
          no-caps
          class="text-white go-btn"
        />
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineProps<{
  tour: {
    id: number;
    title: string;
    price: number;
    image: string;
    location: string;
    hotel_name: string;
    hotel_type: string;
    hotel_rating: string;
    food_type: string;
    description: string;
  };
}>();

const isFavorite = ref(false);
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

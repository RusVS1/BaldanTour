<template>
  <div class="column">
    <TourCard v-for="tour in tours" :key="tour.id" :tour="tour" class="tour-card-item" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import TourCard from './TourCard.vue';

const tours = ref([
  {
    id: 1,
    title: 'Название тура',
    price: 121232112,
    image: '',
    location: 'Местонахождение отдыха',
    hotel_name: 'Название',
    hotel_type: 'Тип отеля',
    hotel_rating: 'Рейтинг',
    food_type: 'Тип питания',
    description:
      'Краткое описание тура Краткое описание тура Краткое описание тура 123142152545354279827 iorghreg hpregh epdirfhgepohgi ',
  },
  {
    id: 2,
    title: 'Название тура',
    price: 121232112,
    image: '',
    location: 'Местонахождение отдыха',
    hotel_name: 'Название',
    hotel_type: 'Тип отеля',
    hotel_rating: 'Рейтинг',
    food_type: 'Тип питания',
    description: 'Краткое описание тура',
  },
  {
    id: 3,
    title: 'Название тура',
    price: 121232112,
    image: '',
    location: 'Местонахождение отдыха',
    hotel_name: 'Название',
    hotel_type: 'Тип отеля',
    hotel_rating: 'Рейтинг',
    food_type: 'Тип питания',
    description: 'Краткое описание тура',
  },
  {
    id: 4,
    title: 'Название тура',
    price: 121232112,
    image: '',
    location: 'Местонахождение отдыха',
    hotel_name: 'Название',
    hotel_type: 'Тип отеля',
    hotel_rating: 'Рейтинг',
    food_type: 'Тип питания',
    description: 'Краткое описание тура',
  },
  {
    id: 5,
    title: 'Название тура',
    price: 121232112,
    image: '',
    location: 'Местонахождение отдыха',
    hotel_name: 'Название',
    hotel_type: 'Тип отеля',
    hotel_rating: 'Рейтинг',
    food_type: 'Тип питания',
    description: 'Краткое описание тура',
  },
  {
    id: 5,
    title: 'Название тура',
    price: 121232112,
    image: '',
    location: 'Местонахождение отдыха',
    hotel_name: 'Название',
    hotel_type: 'Тип отеля',
    hotel_rating: 'Рейтинг',
    food_type: 'Тип питания',
    description: 'Краткое описание тура',
  },
  {
    id: 5,
    title: 'Название тура',
    price: 121232112,
    image: '',
    location: 'Местонахождение отдыха',
    hotel_name: 'Название',
    hotel_type: 'Тип отеля',
    hotel_rating: 'Рейтинг',
    food_type: 'Тип питания',
    description: 'Краткое описание тура',
  },
]);
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

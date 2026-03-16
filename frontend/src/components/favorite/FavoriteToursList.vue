<template>
  <div class="column">
    <TourCard v-for="tour in favorite_tours" :key="tour.id" :tour="tour" class="tour-card-item" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import TourCard from '../home/TourCard.vue';

const favorite_tours = ref([
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
    description: 'Краткое описание тура',
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
.tour-card-item:last-child {
  border-bottom-right-radius: 20px !important;
}

@media (max-width: 1023px) {
  .tour-card-item:last-child {
    border-bottom-left-radius: 20px !important;
  }
}
</style>

<template>
  <q-card
    class="row no-wrap shadow-5 rounded q-pa-lg border-radius-md"
    style="max-width: 1024px; width: 90%"
  >
    <div class="col-6 gt-sm">
      <q-img src="../images/authphoto.jpg" ratio="1" class="border-radius-md" />
    </div>

    <div class="col-12 col-md-6 flex column justify-center q-pa-xl">
      <div class="text-h5 text-primary">
        {{ title }}
      </div>

      <div class="text-subtitle2 text-primary q-mb-md custom-opacity">
        Добро пожаловать в
        <span class="brand-font">BaldanTour</span>
      </div>

      <q-input v-model="login" outlined rounded label="Логин" class="q-mb-md" />

      <q-input v-model="password" outlined rounded type="password" label="Пароль" class="q-mb-md" />

      <router-link :to="switchLink" class="text-primary self-end q-mb-sm custom-opacity">
        {{ switchText }}
      </router-link>

      <q-btn
        :label="buttonText"
        color="secondary"
        unelevated
        rounded
        size="lg"
        class="full-width"
      />
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

type Mode = 'login' | 'register';

const props = defineProps<{
  mode: Mode;
}>();

const login = ref<string>('');
const password = ref<string>('');

const title = computed(() => (props.mode === 'login' ? 'Вход' : 'Регистрация'));

const buttonText = computed(() => (props.mode === 'login' ? 'Войти' : 'Сохранить'));

const switchText = computed(() =>
  props.mode === 'login' ? 'Ещё нет аккаунта?' : 'У меня уже есть аккаунт',
);

const switchLink = computed(() => (props.mode === 'login' ? '/register' : '/login'));
</script>

<style scoped>
.brand-font {
  font-family: 'Inspiration', cursive;
  font-size: 20px;
}
</style>

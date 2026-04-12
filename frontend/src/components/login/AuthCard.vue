<template>
  <q-card
    class="row no-wrap shadow-5 rounded q-pa-lg border-radius-md"
    style="max-width: 1024px; width: 90%"
  >
    <div class="col-6 gt-sm">
      <q-img src="../../images/authphoto.png" ratio="1" class="border-radius-md" />
    </div>

    <div class="col-12 col-md-6 flex column justify-center q-pa-xl">
      <div class="text-h5 text-primary">{{ title }}</div>

      <div class="text-subtitle2 text-primary q-mb-md custom-opacity">
        Добро пожаловать в <span class="brand-font">BaldanTour</span>
      </div>

      <q-input
        v-model="login"
        outlined
        rounded
        label="Логин"
        hint="3-32 символа: латиница, цифры, точка, дефис или подчёркивание"
        class="q-mb-md"
        :error="!!errors.login"
        :error-message="errors.login"
        @blur="validateLogin"
        @keyup.enter="handleSubmit"
      />

      <q-input
        v-model="password"
        outlined
        rounded
        :type="showPassword ? 'text' : 'password'"
        label="Пароль"
        hint="Минимум 8 символов, без пробелов, максимум 128 символов"
        class="q-mb-md"
        :error="!!errors.password"
        :error-message="errors.password"
        @blur="validatePassword"
        @keyup.enter="handleSubmit"
      >
        <template #append>
          <q-icon
            :name="showPassword ? 'visibility_off' : 'visibility'"
            class="cursor-pointer"
            @click="showPassword = !showPassword"
          />
        </template>
      </q-input>

      <div v-if="errors.api" class="text-negative q-mb-md text-center">
        {{ errors.api }}
      </div>

      <router-link :to="switchLink" class="text-primary self-end q-mb-sm custom-opacity">
        {{ switchText }}
      </router-link>

      <q-btn
        :label="buttonText"
        color="secondary"
        unelevated
        rounded
        size="lg"
        no-caps
        class="full-width"
        :loading="loading"
        @click="handleSubmit"
      />
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ApiError } from 'src/api/api';
import { useAuthStore } from 'src/stores/auth';

type Mode = 'login' | 'register';

const props = defineProps<{ mode: Mode }>();

const login = ref('');
const password = ref('');
const loading = ref(false);
const showPassword = ref(false);

const errors = reactive({
  login: '',
  password: '',
  api: '',
});

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const title = computed(() => (props.mode === 'login' ? 'Вход' : 'Регистрация'));
const buttonText = computed(() => (props.mode === 'login' ? 'Войти' : 'Создать аккаунт'));
const switchText = computed(() =>
  props.mode === 'login' ? 'Ещё нет аккаунта?' : 'У меня уже есть аккаунт',
);
const switchLink = computed(() => (props.mode === 'login' ? '/register' : '/login'));

function validateLogin() {
  const value = login.value.trim();
  if (!value) {
    errors.login = 'Введите логин';
    return false;
  }
  if (!/^[A-Za-z0-9_.-]{3,32}$/.test(value)) {
    errors.login = 'Логин: 3-32 символа, латиница, цифры, . _ -';
    return false;
  }
  errors.login = '';
  return true;
}

function validatePassword() {
  if (!password.value) {
    errors.password = 'Введите пароль';
    return false;
  }
  if (password.value.length < 8) {
    errors.password = 'Минимум 8 символов';
    return false;
  }
  if (password.value.length > 128) {
    errors.password = 'Максимум 128 символов';
    return false;
  }
  if (/\s/.test(password.value)) {
    errors.password = 'Пароль не должен содержать пробелы';
    return false;
  }
  errors.password = '';
  return true;
}

function clearErrors() {
  errors.login = '';
  errors.password = '';
  errors.api = '';
}

async function handleSubmit() {
  clearErrors();

  const isLoginValid = validateLogin();
  const isPasswordValid = validatePassword();

  if (!isLoginValid || !isPasswordValid) return;

  loading.value = true;

  try {
    if (props.mode === 'login') {
      await auth.login(login.value.trim(), password.value);
    } else {
      await auth.register(login.value.trim(), password.value);
    }
    const redirect = (route.query.redirect as string) || '/';
    await router.push(redirect);
  } catch (e: unknown) {
    if (e instanceof ApiError) {
      errors.api = e.message || 'Ошибка авторизации';
    } else if (e instanceof Error) {
      errors.api = e.message;
    } else {
      errors.api = 'Неизвестная ошибка';
    }
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.brand-font {
  font-family: 'Inspiration', cursive;
  font-size: 20px;
}
</style>

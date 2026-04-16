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
        Добро пожаловать в
        <span class="brand-font">BaldanTour</span>
      </div>

      <q-input
        v-model="login"
        outlined
        rounded
        label="Логин"
        class="q-mb-md"
        :error="!!errors.login"
        :error-message="errors.login"
        @blur="validateLogin"
      />

      <q-input
        v-model="password"
        outlined
        rounded
        type="password"
        label="Пароль"
        class="q-mb-md"
        :error="!!errors.password"
        :error-message="errors.password"
        @blur="validatePassword"
      />

      <div v-if="errors.api" class="q-mb-md text-center" style="color: #c50000;">
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
import { computed, ref, reactive } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from 'src/stores/auth';
import { ApiError } from 'src/api/api';

type Mode = 'login' | 'register';

const props = defineProps<{ mode: Mode }>();

const login = ref('');
const password = ref('');
const loading = ref(false);

const errors = reactive({
  login: '',
  password: '',
  api: '',
});

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const title = computed(() => (props.mode === 'login' ? 'Вход' : 'Регистрация'));
const buttonText = computed(() => (props.mode === 'login' ? 'Войти' : 'Сохранить'));
const switchText = computed(() =>
  props.mode === 'login' ? 'Ещё нет аккаунта?' : 'У меня уже есть аккаунт',
);
const switchLink = computed(() => (props.mode === 'login' ? '/register' : '/login'));
const loginRegex = /^[A-Za-z0-9._-]+$/;
const passwordRegex = /^[A-Za-z0-9!@#$%^&*()_+=-]+$/;

function validateLogin() {
  if (!login.value.trim()) {
    errors.login = 'Введите логин';
    return false;
  }

  if (login.value.length < 6 || login.value.length > 24) {
    errors.login = 'Логин должен быть от 6 до 24 символов';
    return false;
  }

  if (!loginRegex.test(login.value)) {
    errors.login = 'Только английские буквы, цифры и некоторые спецсимволы';
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

  if (password.value.length < 8 || password.value.length > 16) {
    errors.password = 'Пароль должен быть от 8 до 16 символов';
    return false;
  }

  if (!passwordRegex.test(password.value)) {
    errors.password = 'Только английские буквы, цифры и спецсимволы';
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
      await auth.login(login.value, password.value);
    } else {
      await auth.register(login.value, password.value);
    }
    const redirect = (route.query.redirect as string) || '/';
    await router.push(redirect);
  } catch (e: unknown) {
    if (e instanceof ApiError) {
      const errorData = e.data as Record<string, unknown> | undefined;

      const getErrorString = (val: unknown): string => {
        if (typeof val === 'string') return val;
        if (Array.isArray(val) && val.length > 0) {
          return getErrorString(val[0]);
        }
        const str = String(val);
        if (str !== '[object Object]') return str;
        return '';
      };

      if (errorData?.login) {
        const loginError = getErrorString(errorData.login);
        if (loginError) errors.login = loginError;
      } else if (errorData?.password) {
        const passwordError = getErrorString(errorData.password);
        if (passwordError) errors.password = passwordError;
      } else if (errorData?.non_field_errors) {
        const apiError = getErrorString(errorData.non_field_errors);
        if (apiError) errors.api = apiError;
      } else {
        if (e.message) errors.api = e.message;
      }
    } else if (e instanceof Error) {
      if (e.message) errors.api = e.message;
    } else {
      errors.api = 'Неизвестная ошибка';
    }

    console.error('Auth error:', e);
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

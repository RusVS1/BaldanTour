<template>
  <q-header elevated class="bg-white text-primary">
    <q-toolbar>
      <q-btn
        flat
        no-caps
        to="/"
        dense
        class="custom-opacity q-ml-sm"
        style="
          font-family: 'Inspiration', cursive;
          font-size: 48px;
          padding: none;
          min-height: unset;
          line-height: 1;
        "
      >
        Baldan Tour
      </q-btn>

      <q-space />

      <div class="row items-center q-gutter-sm q-mr-md" style="font-size: 24px">
        <div>$ {{ usdRate }}</div>
        <div>|</div>
        <div>€ {{ eurRate }}</div>
      </div>

      <q-btn v-if="!isAuth" flat no-caps label="Вход" to="/login" style="font-size: 24px" />

      <q-btn v-if="isAuth" flat no-caps label="Избранное" to="/favorite" style="font-size: 24px">
        <q-icon name="favorite" size="40px" class="q-ml-sm" style="color: #dd5555" />
      </q-btn>
      <q-btn v-if="isAuth" flat round icon="person" style="font-size: 24px">
        <q-menu anchor="bottom right" self="top right" style="font-size: 24px" class="text-primary">
          <q-list style="min-width: 150px">
            <q-item>
              <q-item-section>{{ auth.user?.username }}</q-item-section>
            </q-item>

            <q-separator />

            <q-item clickable v-ripple @click="handleLogout">
              <q-item-section>Выход</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-btn>
    </q-toolbar>
  </q-header>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from 'src/stores/auth';
import { getFxRates, type FxResponse } from 'src/api/fx';

const auth = useAuthStore();
const router = useRouter();

const isAuth = computed(() => !!auth.user);

const fx = ref<FxResponse | null>(null);
const isFxLoading = ref(false);

async function loadFx() {
  try {
    isFxLoading.value = true;
    fx.value = await getFxRates();
  } catch (e) {
    console.error('Ошибка загрузки курса', e);
  } finally {
    isFxLoading.value = false;
  }
}

onMounted(() => {
  void loadFx();

  setInterval(
    () => {
      void loadFx();
    },
    1000 * 60 * 10,
  );
});

const usdRate = computed(() => (fx.value ? fx.value.usd_to_rub.toFixed(2) : '...'));

const eurRate = computed(() => (fx.value ? fx.value.eur_to_rub.toFixed(2) : '...'));

async function handleLogout() {
  await auth.logout();
  await router.push('/');
}
</script>

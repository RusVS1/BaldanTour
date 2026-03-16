<template>
  <q-card class="bg-blue q-pa-lg rounded-borders">
    <div class="q-mb-md row items-center q-gutter-md">
      <div class="text-white custom-font-size">Поиск</div>
      <div class="tour-switch">
        <div class="tour-switch-slider" :class="{ hot: tab === 'hot', ai: tab === 'ai' }" />
        <button class="tour-switch-btn" :class="{ active: tab === 'tours' }" @click="tab = 'tours'">
          Туры
        </button>

        <button class="tour-switch-btn" :class="{ active: tab === 'hot' }" @click="tab = 'hot'">
          Горящие туры 🔥
        </button>

        <button class="tour-switch-btn" :class="{ active: tab === 'ai' }" @click="tab = 'ai'">
          Подбор туров ИИ
        </button>
      </div>
    </div>

    <div v-if="tab !== 'ai'" class="row q-col-gutter-xs items-center">
      <div class="col-12 col-md">
        <q-select
          v-model="form.from"
          :options="fromOptions"
          @filter="filterFrom"
          label="Откуда"
          options-dense
          filled
          use-input
          fill-input
          hide-selected
          bg-color="white"
          label-color="primary"
          input-debounce="0"
          input-class="custom-font-size text-primary"
          popup-content-class="custom-font-size text-primary"
          dropdown-icon="keyboard_double_arrow_down"
          class="custom-arrow-blue"
        />
      </div>

      <div class="col-12 col-md">
        <q-select
          v-model="form.to"
          :options="toOptions"
          @filter="filterTo"
          label="Куда"
          options-dense
          filled
          use-input
          fill-input
          hide-selected
          bg-color="white"
          label-color="primary"
          input-debounce="0"
          input-class="custom-font-size text-primary"
          popup-content-class="custom-font-size text-primary"
          dropdown-icon="keyboard_double_arrow_down"
          class="custom-arrow-blue"
        />
      </div>

      <div class="col-12 col-md">
        <q-input
          v-model="dateModel"
          label="Даты вылета"
          filled
          bg-color="white"
          label-color="primary"
          readonly
          input-class="custom-font-size text-primary"
          class="custom-arrow-blue"
        >
          <template #append>
            <q-icon name="event" class="cursor-pointer" />
            <q-menu anchor="bottom right" self="top right">
              <q-date v-model="form.date" range mask="DD.MM" color="blue" />
            </q-menu>
          </template>
        </q-input>
      </div>

      <div class="col-12 col-md">
        <q-input
          v-model="nightsModel"
          label="Ночей"
          filled
          bg-color="white"
          label-color="primary"
          readonly
          input-class="custom-font-size text-primary"
          class="custom-arrow-blue"
        >
          <template #append>
            <q-icon name="keyboard_double_arrow_down" class="cursor-pointer" />
            <q-menu anchor="bottom right" self="top right" auto-close>
              <div
                class="q-pa-sm"
                style="
                  display: grid;
                  grid-template-columns: repeat(6, 1fr);
                  gap: 4px;
                  width: max-content;
                "
              >
                <q-btn
                  v-for="n in 30"
                  :key="n"
                  size="md"
                  flat
                  outline
                  :label="n"
                  class="text-primary"
                  @click="form.nights = n"
                />
              </div>
            </q-menu>
          </template>
        </q-input>
      </div>

      <div class="col-12 col-md">
        <q-input
          v-model="touristsModel"
          :value="`${form.tourists.adults} взр. • ${form.tourists.children} дет.`"
          label="Туристы"
          filled
          readonly
          class="custom-arrow-blue"
          input-class="custom-font-size text-primary"
          bg-color="white"
          label-color="primary"
        >
          <template #append>
            <q-icon name="keyboard_double_arrow_down" class="cursor-pointer" />
            <q-menu anchor="bottom right" self="top right">
              <div class="q-pa-md custom-font-size" style="min-width: 200px">
                <div class="row justify-between items-center q-mb-sm text-primary">
                  <div>Взрослые</div>
                  <q-btn-group flat>
                    <q-btn
                      dense
                      flat
                      icon="remove"
                      @click="form.tourists.adults > 1 && form.tourists.adults--"
                    />
                    <q-btn dense flat :label="form.tourists.adults" />
                    <q-btn dense flat icon="add" @click="form.tourists.adults++" />
                  </q-btn-group>
                </div>
                <div class="row justify-between items-center text-primary">
                  <div>Дети</div>
                  <q-btn-group flat>
                    <q-btn
                      dense
                      flat
                      icon="remove"
                      @click="form.tourists.children > 0 && form.tourists.children--"
                    />
                    <q-btn dense flat :label="form.tourists.children" />
                    <q-btn dense flat icon="add" @click="form.tourists.children++" />
                  </q-btn-group>
                </div>
              </div>
            </q-menu>
          </template>
        </q-input>
      </div>

      <div class="col-auto q-ml-sm">
        <q-btn
          label="Найти"
          color="white"
          size="lg"
          no-caps
          text-color="primary"
          unelevated
          style="height: 56px"
        />
      </div>
    </div>

    <div v-else class="row q-col-gutter-xs items-center">
      <div class="col">
        <q-input
          v-model="aiQuery"
          label="Опишите ваш идеальный отдых"
          filled
          bg-color="white"
          label-color="primary"
          input-class="custom-font-size text-primary"
          class="custom-arrow-blue"
          type="textarea"
          autogrow
          rows="3"
        />
      </div>
      <div class="col-auto q-ml-sm">
        <q-btn
          label="Найти"
          color="white"
          size="lg"
          no-caps
          text-color="primary"
          unelevated
          style="height: 56px"
        />
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue';

const tab = ref<'tours' | 'hot' | 'ai'>('tours');
const aiQuery = ref('');

const form = reactive({
  from: null as string | null,
  to: null as string | null,
  date: {
    from: '',
    to: '',
  },
  nights: null as number | null,
  tourists: {
    adults: 0,
    children: 0,
  },
});

const cities = ['Москва', 'Санкт-Петербург', 'Казань', 'Новосибирск'];

const fromOptions = ref([...cities]);
const toOptions = ref([...cities]);

type FilterUpdate = (callback: () => void) => void;

function filterFrom(val: string, update: FilterUpdate) {
  update(() => {
    const needle = val.toLowerCase();
    fromOptions.value = cities.filter((v) => v.toLowerCase().includes(needle));
  });
}

function filterTo(val: string, update: FilterUpdate) {
  update(() => {
    const needle = val.toLowerCase();
    toOptions.value = cities.filter((v) => v.toLowerCase().includes(needle));
  });
}

const touristsModel = computed({
  get() {
    const { adults, children } = form.tourists;
    const parts: string[] = [];

    if (adults > 0) {
      parts.push(adults === 1 ? '1 взрослый' : `${adults} взрослых`);
    }

    if (children > 0) {
      parts.push(children === 1 ? '1 ребёнок' : `${children} детей`);
    }

    return parts.join(' • ');
  },
  set() {},
});

const nightsModel = computed({
  get() {
    const n = form.nights;
    if (!n) return '';

    const mod10 = n % 10;
    const mod100 = n % 100;

    if (mod10 === 1 && mod100 !== 11) return `${n} ночь`;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${n} ночи`;
    return `${n} ночей`;
  },
  set() {},
});

const dateModel = computed({
  get() {
    const { from, to } = form.date;
    if (from && to) return `${from} - ${to}`;
    else if (from) return from;
    else return '';
  },
  set() {},
});
</script>

<style scoped>
.tour-switch {
  position: relative;
  display: flex;
  align-items: center;
  background: #7cb3dd;
  border-radius: 40px;
  padding: 6px;
  width: 600px;
  border: #d6edff;
}

.tour-switch-btn {
  flex: 1;
  border: none;
  background: transparent;
  color: white;
  font-size: 20px;
  padding: 16px 0px;
  border-radius: 30px;
  cursor: pointer;
  z-index: 2;
  transition: color 0.25s;
  text-align: center;
}

.tour-switch-btn.active {
  color: #3c83b9;
}

.tour-switch-slider {
  position: absolute;
  width: calc(100% / 3 - 4px);
  height: calc(100% - 12px);
  background: white;
  border-radius: 30px;
  transition: transform 0.35s ease;
}

.tour-switch-slider.hot {
  transform: translateX(100%);
  background: #dd5555;
}

.tour-switch-slider.ai {
  transform: translateX(200%);
}

.tour-switch-btn:nth-child(3).active {
  color: white;
}
</style>

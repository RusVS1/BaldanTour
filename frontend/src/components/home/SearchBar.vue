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
          v-model="from"
          :options="fromOptions"
          option-label="label"
          option-value="value"
          map-options
          emit-value
          @filter="filterFrom"
          label="Откуда *"
          options-dense
          filled
          use-input
          fill-input
          hide-selected
          hide-bottom-space
          bg-color="white"
          label-color="primary"
          input-debounce="0"
          input-class="custom-font-size text-primary"
          popup-content-class="custom-font-size text-primary"
          dropdown-icon="keyboard_double_arrow_down"
          class="custom-arrow-blue"
          @blur="touched.from = true"
        >
          <q-tooltip anchor="top middle" self="bottom middle" style="font-size: 12px">
            Город, из которого начнётся ваше путешествие
          </q-tooltip>
        </q-select>
      </div>

      <div class="col-12 col-md">
        <q-select
          v-model="to"
          :options="toOptions"
          option-label="label"
          option-value="value"
          map-options
          emit-value
          @filter="filterTo"
          label="Куда *"
          options-dense
          filled
          use-input
          fill-input
          hide-selected
          hide-bottom-space
          bg-color="white"
          label-color="primary"
          input-debounce="0"
          input-class="custom-font-size text-primary"
          popup-content-class="custom-font-size text-primary"
          dropdown-icon="keyboard_double_arrow_down"
          class="custom-arrow-blue"
          @blur="touched.to = true"
        >
          <q-tooltip anchor="top middle" self="bottom middle" style="font-size: 12px">
            Страна, куда вы хотите поехать
          </q-tooltip>
        </q-select>
      </div>

      <div class="col-12 col-md">
        <q-input
          v-model="dateModel"
          label="Даты вылета *"
          filled
          bg-color="white"
          label-color="primary"
          readonly
          :disable="tab === 'hot'"
          hide-bottom-space
          input-class="custom-font-size text-primary"
          class="custom-arrow-blue"
          @blur="touched.date = true"
        >
          <template #append>
            <q-icon name="event" class="cursor-pointer" />
            <q-menu anchor="bottom right" self="top right">
              <q-date v-model="form.date" range mask="DD.MM" color="blue" />
            </q-menu>
          </template>
          <q-tooltip anchor="top middle" self="bottom middle" style="font-size: 12px">
            Выберите период для поиска туров
          </q-tooltip>
        </q-input>
      </div>

      <div class="col-12 col-md">
        <q-input
          v-model="nightsModel"
          label="Ночей *"
          filled
          bg-color="white"
          label-color="primary"
          readonly
          hide-bottom-space
          input-class="custom-font-size text-primary"
          class="custom-arrow-blue"
        >
          <template #append>
            <q-icon name="keyboard_double_arrow_down" class="cursor-pointer" />
            <q-menu anchor="bottom right" self="top right" auto-close>
              <div
                class="q-pa-sm"
                style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 4px"
              >
                <q-btn
                  v-for="n in 30"
                  :key="n"
                  size="md"
                  flat
                  outline
                  :label="n"
                  class="text-primary"
                  @click="
                    form.nights = n;
                    touched.nights = true;
                  "
                />
              </div>
            </q-menu>
          </template>
          <q-tooltip anchor="top middle" self="bottom middle" style="font-size: 12px">
            Сколько ночей вы планируете отдохнуть
          </q-tooltip>
        </q-input>
      </div>

      <div class="col-12 col-md">
        <q-input
          v-model="touristsModel"
          :value="`${form.tourists.adults} взр. • ${form.tourists.children} дет.`"
          label="Туристы *"
          filled
          readonly
          hide-bottom-space
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
                    <q-btn
                      dense
                      flat
                      icon="add"
                      @click="
                        form.tourists.adults++;
                        touched.tourists = true;
                      "
                    />
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
                    <q-btn
                      dense
                      flat
                      icon="add"
                      @click="
                        form.tourists.children++;
                        touched.tourists = true;
                      "
                    />
                  </q-btn-group>
                </div>
              </div>
            </q-menu>
          </template>
          <q-tooltip anchor="top middle" self="bottom middle" style="font-size: 12px">
            Количество взрослых и детей, которые поедут в тур
          </q-tooltip>
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
          hide-bottom-space
          style="height: 56px"
          :disable="!isFormValid"
          @click="handleSearch"
        >
          <q-tooltip
            v-if="!isFormValid"
            anchor="top middle"
            self="bottom middle"
            style="font-size: 12px"
          >
            Заполните все обязательные поля
          </q-tooltip>
        </q-btn>
      </div>
    </div>

    <div v-else class="row q-col-gutter-xs items-center">
      <div class="col">
        <q-input
          v-model="aiQuery"
          label="Опишите ваш идеальный отдых*"
          filled
          hide-bottom-space
          bg-color="white"
          label-color="primary"
          input-class="custom-font-size text-primary"
          class="custom-arrow-blue"
          type="textarea"
          autogrow
          rows="3"
          @blur="touched.aiQuery = true"
        >
          <q-tooltip anchor="top middle" self="bottom middle" style="font-size: 12px">
            Например: "Пляжный отдых в Турции, всё включено, 7 ночей, 2 взрослых и ребёнок"
          </q-tooltip>
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
          :disable="!isAiFormValid"
          @click="handleAiSearch"
        >
          <q-tooltip
            v-if="!isAiFormValid"
            anchor="top middle"
            self="bottom middle"
            style="font-size: 12px"
          >
            Введите описание вашего идеального отдыха
          </q-tooltip>
        </q-btn>
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, watch } from 'vue';
import {
  getFilterOptions,
  formatOptions,
  type FilterOption,
  type RegularSearchParams,
  type AiSearchParams,
} from 'src/api/filters';

const emit = defineEmits<{
  (e: 'search', params: RegularSearchParams, isAi: false): void;
  (e: 'search', params: AiSearchParams, isAi: true): void;
}>();

const tab = ref<'tours' | 'hot' | 'ai'>('tours');
const aiQuery = ref('');

const touched = reactive({
  from: false,
  to: false,
  date: false,
  nights: false,
  tourists: false,
  aiQuery: false,
});

const from = ref<string | null>(null);
const to = ref<string | null>(null);

const form = reactive({
  date: { from: '', to: '' },
  nights: null as number | null,
  tourists: { adults: 1, children: 0 },
});

const fromOptions = ref<FilterOption[]>([]);
const toOptions = ref<FilterOption[]>([]);

let townFromCache: FilterOption[];
let countryCache: FilterOption[];

onMounted(async () => {
  const [townFrom, country] = await Promise.all([
    getFilterOptions.townFrom(),
    getFilterOptions.country(),
  ]);

  townFromCache = townFrom.values;
  countryCache = country.values;

  fromOptions.value = formatOptions(townFromCache);
  toOptions.value = formatOptions(countryCache);
});

type FilterUpdate = (callback: () => void) => void;

function filterFrom(val: string, update: FilterUpdate) {
  update(() => {
    const needle = val.toLowerCase();
    fromOptions.value = formatOptions(
      townFromCache.filter((opt) => opt.label.toLowerCase().includes(needle)),
    );
  });
}

function filterTo(val: string, update: FilterUpdate) {
  update(() => {
    const needle = val.toLowerCase();
    toOptions.value = formatOptions(
      countryCache.filter((opt) => opt.label.toLowerCase().includes(needle)),
    );
  });
}

const touristsModel = computed({
  get() {
    const { adults, children } = form.tourists;
    const parts: string[] = [];
    if (adults > 0) parts.push(adults === 1 ? '1 взрослый' : `${adults} взрослых`);
    if (children > 0) parts.push(children === 1 ? '1 ребёнок' : `${children} детей`);
    return parts.join(' • ');
  },
  set() {},
});

const nightsModel = computed({
  get() {
    const n = form.nights;
    if (!n) return '';
    const mod10 = n % 10,
      mod100 = n % 100;
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
    return from || '';
  },
  set() {},
});

const formatDate = (date: Date): string => {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  return `${day}.${month}`;
};

const setHotToursDate = () => {
  const start = new Date();
  const end = new Date();
  end.setDate(start.getDate() + 14);

  form.date = {
    from: formatDate(start),
    to: formatDate(end),
  };
};

watch(
  tab,
  (newTab) => {
    if (newTab === 'hot') {
      setHotToursDate();
    }
  },
  { immediate: true },
);

const isFormValid = computed(
  () =>
    !!from.value && !!to.value && !!form.date.from && !!form.nights && form.tourists.adults >= 1,
);

const isAiFormValid = computed(() => aiQuery.value.trim().length >= 10);

function handleSearch() {
  touched.from = touched.to = touched.date = touched.nights = touched.tourists = true;
  if (!isFormValid.value) return;

  const params: RegularSearchParams = {
    from: from.value!,
    to: to.value!,
    dateFrom: form.date.from,
    dateTo: form.date.to,
    nights: form.nights,
    adults: form.tourists.adults,
    children: form.tourists.children,
  };

  emit('search', params, false);
}

function handleAiSearch() {
  touched.aiQuery = true;
  if (!isAiFormValid.value) {
    return;
  }
  const params: AiSearchParams = {
    aiQuery: aiQuery.value.trim(),
    tab: 'ai',
  };
  emit('search', params, true);
}
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
  padding: 16px 0;
  border-radius: 30px;
  cursor: pointer;
  z-index: 2;
  transition: color 0.25s;
  text-align: center;
}
.tour-switch-btn.active {
  color: var(--q-secondary);
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

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
        <div>$ курс</div>
        <div>|</div>
        <div>€ курс</div>
      </div>

      <q-btn v-if="!isAuth" flat no-caps label="Вход" to="/login" style="font-size: 24px" />

      <q-btn v-if="isAuth" flat no-caps label="Избранное" to="/favorite" style="font-size: 24px">
        <q-icon name="favorite" size="40px" class="q-ml-sm" style="color: #dd5555" />
      </q-btn>
      <q-btn v-if="isAuth" flat round icon="person" style="font-size: 24px">
        <q-menu anchor="bottom right" self="top right" style="font-size: 24px" class="text-primary">
          <q-list style="min-width: 150px">
            <q-item>
              <q-item-section>
                {{ userLogin }}
              </q-item-section>
            </q-item>

            <q-separator />

            <q-item clickable v-ripple @click="logout">
              <q-item-section> Выход </q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-btn>
    </q-toolbar>
  </q-header>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const isAuth = ref(true);

const userLogin = ref('Логин_пользователя');

function logout() {
  console.log('Выход из аккаунта');
}
</script>

<style scoped></style>

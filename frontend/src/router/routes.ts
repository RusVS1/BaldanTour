import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        redirect: '/login',
      },

      {
        path: 'login',
        name: 'login',
        component: () => import('pages/LoginPage.vue'),
      },

      {
        path: 'register',
        name: 'register',
        component: () => import('pages/RegisterPage.vue'),
      },
    ],
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;

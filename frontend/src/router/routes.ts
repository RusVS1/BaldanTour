import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('pages/HomePage.vue') },
      {
        path: '/login',
        name: 'login',
        component: () => import('pages/LoginPage.vue'),
        meta: { guestOnly: true },
      },
      {
        path: 'register',
        name: 'register',
        component: () => import('pages/RegisterPage.vue'),
        meta: { guestOnly: true },
      },
      {
        path: 'favorite',
        name: 'favorite',
        component: () => import('pages/FavoritePage.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },

  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
import { useAuthStore } from 'src/stores/auth';
import type { Router } from 'vue-router';

export function setupRouterGuards(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore();

    if (auth.user === null) {
      try {
        await auth.fetchUser();
      } catch (e) {
        console.warn('fetchUser failed', e);
      }
    }

    if (to.meta.requiresAuth && !auth.user) {
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      };
    }

    if (to.meta.guestOnly && auth.user) {
      return '/';
    }

    return true;
  });
}

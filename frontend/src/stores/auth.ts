import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getMeApi, loginApi, logoutApi, registerApi } from 'src/api/auth';

export type User = {
  id: number;
  username: string;
  is_staff: boolean;
  is_superuser: boolean;
};

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const isAuth = computed(() => !!user.value);

  async function fetchUser() {
    try {
      isLoading.value = true;
      const res = await getMeApi();
      user.value = res.user;
    } catch {
      user.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  async function login(username: string, password: string) {
    await loginApi(username, password);
    await fetchUser();
  }

  async function register(username: string, password: string) {
    await registerApi(username, password);
    await fetchUser();
  }

  async function logout() {
    await logoutApi();
    user.value = null;
  }

  return {
    user,
    isLoading,
    isAuth,
    fetchUser,
    login,
    register,
    logout,
  };
});

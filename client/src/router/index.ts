import { RouterOptions, createWebHistory } from 'vue-router';
import HomePage from '../views/HomePage.vue';
import DisplayAdmin from '../views/Admin/DisplayAdmin.vue';

function makeOptions(): RouterOptions {
  return {
    history: createWebHistory(),
    routes: [
      {
        path: '/',
        // component: HomePage,
        component: HomePage,
      },
      {
        path: '/admin',
        // component: HomePage,
        component: DisplayAdmin,
      },

    ],
  };
}

export default makeOptions;

import { RouterOptions, createWebHistory } from 'vue-router';
import HomePage from '../views/HomePage.vue';

function makeOptions(): RouterOptions {
  return {
    history: createWebHistory(),
    routes: [
      {
        path: '/',
        // component: HomePage,
        component: HomePage,
      },
    ],
  };
}

export default makeOptions;

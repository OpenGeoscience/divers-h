import { createApp } from 'vue';
import { createRouter } from 'vue-router';
import { createVuetify } from 'vuetify';
import App from './App.vue';
import 'vuetify/styles';
import '@mdi/font/css/materialdesignicons.css';

import oauthClient, { maybeRestoreLogin } from './plugins/Oauth';
import UVdatApi from './api/UVDATApi';
import makeOptions from './router';
import PopupComponent from './components/PopupComponent.vue';

const app = createApp(App);
const Vuetify = createVuetify({});

maybeRestoreLogin().then(async () => {
  if (!(await UVdatApi.fetchCurrentUser())) {
    oauthClient.redirectToLogin();
    return;
  }

  /*
  The router must not be initialized until after the oauth flow is complete, because it
  stores the initial history state at the time of its construction, and we don't want it
  to capture that initial state until after we remove any OAuth response params from the URL.
  */
  const router = createRouter(makeOptions());
  app.use(router);
  app.use(Vuetify);
  app.provide('oauthClient', oauthClient);
  // Object.assign(axiosInstance.defaults.headers.common, oauthClient.authHeaders);
  app.mount('#app');
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any, vue/max-len
const createPopup = (data: Record<string, any>[]) => createApp(PopupComponent, { data }).use(Vuetify);

export default createPopup;

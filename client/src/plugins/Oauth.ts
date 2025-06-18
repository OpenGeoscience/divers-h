/* eslint-disable vue/max-len */
import OauthClient from '@resonant/oauth-client';
import { ref } from 'vue';
import UVdatApi from '../api/UVDATApi';
import { createS3ffClient } from './S3FileField';

// eslint-disable-next-line no-restricted-globals
const redirectUrl = new URL((import.meta.env.VUE_APP_LOGIN_REDIRECT || location.origin) as string, window.location.origin);
const baseUrl = new URL(import.meta.env.VUE_APP_OAUTH_API_ROOT as string || 'http://localhost:8000/oauth/', window.location.origin);
const clientId = (import.meta.env.VUE_APP_OAUTH_CLIENT_ID as string || 'devClientId');
const oauthClient = new OauthClient(baseUrl, clientId, { redirectUrl });

export const loggedIn = ref(oauthClient.isLoggedIn);

export async function logout() {
  await oauthClient?.logout();
  loggedIn.value = false;
}

export async function maybeRestoreLogin() {
  await oauthClient.maybeRestoreLogin();
  loggedIn.value = oauthClient.isLoggedIn;
  UVdatApi.initialize(oauthClient);
  createS3ffClient(UVdatApi.apiClient);
}

export default oauthClient;

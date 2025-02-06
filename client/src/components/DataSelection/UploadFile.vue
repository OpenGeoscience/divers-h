<script lang="ts">
import { defineComponent, ref } from 'vue';
import { S3FileFieldResultState } from 'django-s3-file-field';
import { getS3ffClient } from '../../plugins/S3FileField';

export default defineComponent({
  emits: ['upload', 'close'],
  setup(_, { emit }) {
    const s3ffClient = getS3ffClient();

    const successDialog = ref(false);
    const uploadLoading = ref(false);
    const uploadProgress = ref<number>(0);
    const uploadFile = ref<File | null>(null);
    const uploadError = ref<unknown>();
    const acceptTypes = ref('.geojson, .json, .tif, .tiff, .zip, .gpkg, .nc');

    const fileInput = ref<HTMLInputElement | null>(null);

    function triggerFileInput() {
      if (fileInput.value) fileInput.value.click();
    }

    async function upload() {
      try {
        uploadLoading.value = true;
        uploadError.value = undefined;
        uploadProgress.value = 0;

        const file = uploadFile.value;
        if (!file) return;

        const uploadResult = await s3ffClient.uploadFile(
          file,
          'core.FileItem.file',
          (progress) => {
            if (progress.state === 1 && progress.uploaded !== undefined && progress.total !== undefined) {
              uploadProgress.value = (progress.uploaded / progress.total) * 100;
            }
          },
        );

        if (uploadResult.state !== S3FileFieldResultState.Successful) {
          const status = ['was aborted', '', 'errored'][uploadResult.state];
          throw new Error(`File upload ${status}`);
        }

        successDialog.value = true;
        emit('upload', { result: uploadResult.value, name: file.name });
      } catch (err) {
        uploadError.value = err;
      } finally {
        uploadLoading.value = false;
      }
    }

    async function handleFileSelected(event: Event) {
      const input = event.target as HTMLInputElement;
      if (!input.files || input.files.length === 0) return;

      // eslint-disable-next-line prefer-destructuring
      uploadFile.value = input.files[0];
      await upload();
    }

    function closeDialogs() {
      successDialog.value = false;
      emit('close');
    }

    return {
      successDialog,
      uploadLoading,
      uploadProgress,
      uploadError,
      acceptTypes,
      fileInput,
      triggerFileInput,
      handleFileSelected,
      closeDialogs,
    };
  },
});
</script>

<template>
  <div>
    <v-btn
      :disabled="uploadLoading"
      color="primary"
      variant="outlined"
      @click="triggerFileInput"
    >
      <template v-if="!uploadLoading">
        Upload File
      </template>
      <template v-else>
        Uploading...
        <v-progress-circular
          :size="24"
          :width="2"
          :model-value="uploadProgress"
          color="primary"
        />
      </template>
    </v-btn>

    <input
      ref="fileInput"
      aria-label="fileinput"
      type="file"
      :accept="acceptTypes"
      style="display: none"
      @change="handleFileSelected"
    />

    <v-alert v-if="uploadError" color="error" dismissible>
      {{ String(uploadError) }}
    </v-alert>
    <v-dialog v-model="successDialog" persistent width="25%">
      <v-card>
        <v-card-title>Upload Successful</v-card-title>
        <v-card-text>
          The file has been successfully uploaded.
          Processing will begin to convert the file into map layers
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeDialogs">
            OK
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

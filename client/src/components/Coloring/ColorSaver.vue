<script lang="ts">
import { PropType, defineComponent, ref } from 'vue';
import MapStore from '../../MapStore';
import { ColorDisplay, VectorMapLayer } from '../../types';

export default defineComponent({
  components: {
  },
  props: {
    data: {
      type: Object as PropType<ColorDisplay>,
      required: true,
    },
    layerId: {
      type: Number,
      required: true,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const saveAsDialog = ref(false);
    const saveAsName = ref('');
    const saveAsDescription = ref('');

    const pushSaveAs = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item: VectorMapLayer) => item.id === props.layerId,
      );
      if (found) {
        if (found.default_style && !found.default_style?.savedColors) {
          found.default_style.savedColors = [];
        }
        if (found.default_style && found.default_style?.savedColors) {
          // find if there is an existing option
          const foundSaveColorIndex = found.default_style.savedColors.findIndex((item) => item.name === saveAsName.value);
          if (foundSaveColorIndex !== -1) {
            found.default_style.savedColors.splice(foundSaveColorIndex, 1, {
              name: saveAsName.value,
              description: saveAsDescription.value,
              color: props.data,
            });
          } else {
            found.default_style.savedColors.push({
              name: saveAsName.value,
              description: saveAsDescription.value,
              color: props.data,
            });
          }
        }
        saveAsDialog.value = false;
      }
    };

    return {
      saveAsDialog,
      saveAsName,
      saveAsDescription,
      pushSaveAs,
    };
  },
});
</script>

<template>
  <v-btn
    color="primary"
    :disabled="disabled"
    @click="saveAsDialog = true"
  >
    Save As...
  </v-btn>
  <v-dialog
    v-model="saveAsDialog"
    width="500"
  >
    <v-card>
      <v-card-title>Save Color Scheme</v-card-title>
      <v-card-text>
        <p>This allows you save the color scheme to be swap between coloring fields</p>
        <v-row>
          <v-text-field
            v-model="saveAsName"
            label="name"
          />
        </v-row>
        <v-row>
          <v-text-field
            v-model="saveAsDescription"
            label="Description"
          />
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-row>
          <v-spacer />
          <v-btn
            color="error"
            @click="saveAsDialog = false; saveAsName = ''; saveAsDescription = '';"
          >
            Cancel
          </v-btn>
          <v-btn
            class="ml-2"
            color="success"
            @click="pushSaveAs"
          >
            Save
          </v-btn>
        </v-row>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.main-area {
  position: absolute;
  top: 65px;
  height: calc(100% - 70px);
  width: 100%;
}
</style>

<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
} from 'vue';
import { VNumberInput } from 'vuetify/labs/VNumberInput';
import { cloneDeep } from 'lodash';

export default defineComponent({
  components: {
    VNumberInput,
  },
  props: {
    colorListing: {
      type: Array as PropType<{ value: number, color: string }[]>,
      required: true,
    },
  },
  emits: ['updateColor'],
  setup(props, { emit }) {
    const localColorConfig: Ref<{ value: number, color: string }[]> = ref(props.colorListing);

    const sortedValues = computed(() => {
      const pairs = cloneDeep(localColorConfig.value);
      return pairs.sort((a, b) => a.value - b.value);
    });
    const addNumber = ref(false);
    const newNumber = ref(0);
    const newColor = ref('#FF0000');

    const addNumberPair = () => {
      localColorConfig.value.push({
        value: newNumber.value,
        color: newColor.value,
      });

      addNumber.value = false;
    };

    const removeNumberPair = (value: number, color: string) => {
      const index = localColorConfig.value.findIndex(
        (item) => item.color === color && item.value === value,
      );
      if (index !== -1) {
        localColorConfig.value.splice(index, 1);
      }
    };

    const updateNumberPair = (
      value: number,
      color: string,
      oldValue: number,
      oldColor: string,
    ) => {
      const index = localColorConfig.value.findIndex(
        (item) => item.color === oldColor && item.value === oldValue,
      );
      if (index !== -1) {
        localColorConfig.value[index] = {
          value,
          color,
        };
      }
    };

    const pushColor = () => {
      localColorConfig.value.sort((a, b) => a.value - b.value);
      emit('updateColor', localColorConfig.value);
    };

    return {
      sortedValues,
      addNumber,
      newNumber,
      newColor,
      addNumberPair,
      removeNumberPair,
      updateNumberPair,
      localColorConfig,
      pushColor,
    };
  },
});
</script>

<template>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col cols="10">
      <p>
        This heatmap color uses the heatmap density to adjust the color range that is displayed.
        Please note that the first color will have its alpha set to transparent so the background is visible.
      </p>
    </v-col>
    <v-col>
      <v-btn @click="addNumber = true">
        Add <v-icon>mdi-plus</v-icon>
      </v-btn>
    </v-col>
  </v-row>
  <v-row
    v-if="addNumber"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-number-input
        v-model="newNumber"
        density="compact"
        label="number"
        control-variant="split"
      />
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: newColor }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          v-model="newColor"
          mode="hex"
        />
      </v-menu>
    </v-col>
    <v-col>
      <v-btn @click="addNumberPair()">
        Add
      </v-btn>
    </v-col>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col>Number</v-col>
    <v-col>Color</v-col>
    <v-col>Delete</v-col>
  </v-row>
  <v-row
    v-for="item in sortedValues"
    :key="`number_color_pair_${item.value}`"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-number-input
        control-variant="split"
        :model-value="item.value"
        density="compact"
        :step="0.1"
        :rules="[v => v >= 0 || 'Must be >= 0', v => v <= 1 || 'Must be <= 1']"
        @change="
          updateNumberPair(
            $event.target._value,
            item.color,
            item.value,
            item.color,
          )
        "
      />
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: item.color }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          mode="hex"
          @update:model-value="
            updateNumberPair(item.value, $event, item.value, item.color)
          "
        />
      </v-menu>
    </v-col>
    <v-col>
      <v-icon @click="removeNumberPair(item.value, item.color)">
        mdi-delete
      </v-icon>
    </v-col>
  </v-row>
  <v-row dense>
    <v-spacer />
    <v-btn
      color="success"
      @click="pushColor()"
    >
      Push Color
    </v-btn>
  </v-row>
</template>

<style scoped>
.color-square {
  width: 25px;
  height: 25px;
  border: 1px solid #000;
  cursor: pointer;
}
</style>

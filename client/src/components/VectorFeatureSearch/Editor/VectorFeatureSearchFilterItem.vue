<script lang="ts">
import {
  PropType, computed, defineComponent, ref, watch,
} from 'vue';
import { AvailablePropertyDisplay } from '../../../types';

export default defineComponent({
  props: {
    value: {
      type: Array as PropType<string[]>,
      required: true,
    },
    availableProperties: {
      type: Object as PropType<Record<string, AvailablePropertyDisplay>>,
      required: true,
    },
  },
  emits: ['update'],
  setup(props, { emit }) {
    const localFilters = ref(props.value);

    const availablePropertyKeys = computed(() => Object.keys(props.availableProperties || {}).map((key) => ({
      title: props.availableProperties?.[key]?.displayName || key,
      value: key,
    })));

    watch(localFilters, () => {
      emit('update', localFilters.value);
    }, { deep: true });

    return {
      localFilters,
      availablePropertyKeys,
    };
  },
});
</script>

<template>
  <v-combobox
    v-model="localFilters"
    :items="availablePropertyKeys"
    label="Filter Key"
    multiple
    chips
    closable-chips
    hide-details
  />
</template>

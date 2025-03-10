<script lang="ts">
import {
  PropType, defineComponent, ref, watch,
} from 'vue';

export default defineComponent({
  props: {
    value: {
      type: Array as PropType<string[]>,
      required: true,
    },
    availablePropertyKeys: {
      type: Object as PropType<{ title: string, value: string }[]>,
      required: true,
    },
  },
  emits: ['update'],
  setup(props, { emit }) {
    const localFilters = ref(props.value);

    watch(localFilters, () => {
      emit('update', localFilters.value);
    }, { deep: true });

    return {
      localFilters,
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

<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
  watch,
} from 'vue';
import { VNumberInput } from 'vuetify/lib/labs/components';
import {
  AnnotationTypes,
  Filter,
  NumberBetweenFilter,
  NumberComparisonFilter,
  StringContainsFilter,
  StringInArrayFilter,
  StringMatchFilter,
} from '../../types';
import { getLayerAvailableProperties } from '../../utils';

export default defineComponent({
  components: {
    VNumberInput,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },

  },
  emits: ['cancel', 'add'],
  setup(props, { emit }) {
    const filterTypes: Ref<Filter['type'][]> = ref(['number', 'string', 'bool']);
    const selectedFilterType: Ref<Filter['type']> = ref('number');
    const selectedOperator: Ref<Filter['operator']> = ref('<');
    const operators = computed(() => {
      if (selectedFilterType.value === 'number') {
        return ['>', '<', '>=', '<=', '==', 'between'];
      } if (selectedFilterType.value === 'string') {
        return ['in', '==', 'contains'];
      } if (selectedFilterType.value === 'bool') {
        return ['=='];
      }
      return [];
    });
    const availableAttributes = computed(
      () => Object.values(
        getLayerAvailableProperties(props.layerId),
      )
        .filter((item) => (item.type === selectedFilterType.value)),
    );

    onMounted(() => {
      const vals = Object.values(getLayerAvailableProperties(props.layerId));
      const stringCount = vals.filter((item) => item.type === 'string').length;
      const numberCount = vals.filter((item) => item.type === 'number').length;
      const boolCount = vals.filter((item) => item.type === 'bool').length;
      filterTypes.value = [];
      if (numberCount) {
        filterTypes.value.push('number');
      }
      if (stringCount) {
        filterTypes.value.push('string');
      }
      if (boolCount) {
        filterTypes.value.push('bool');
      }
    });

    const selectedKey: Ref<string | ''> = ref(availableAttributes.value[0]?.key || '');

    watch(selectedFilterType, () => {
      selectedKey.value = availableAttributes.value[0].key;
      selectedOperator.value = operators.value[0] as Filter['operator'];
    });

    const name = ref('');
    const description = ref('');
    const layers: Ref<AnnotationTypes[]> = ref(['line', 'circle', 'fill', 'fill-extrusion', 'text']);
    const rangeValue = ref([0, 1]);
    const value: Ref<number | string | boolean> = ref(0);
    const values: Ref<string[]> = ref([]);

    const toggleLayerAnnotation = (layerType: AnnotationTypes) => {
      if (layers.value.includes(layerType)) {
        const index = layers.value.findIndex((item) => (item === layerType));
        layers.value.splice(index);
      } else {
        layers.value.push(layerType);
      }
    };

    const selectedAttributeValue = computed(() => {
      const found = availableAttributes.value.find((item) => item.key === selectedKey.value);
      return found;
    });

    const possibleValues = computed(() => {
      const found = availableAttributes.value.find((item) => item.key === selectedKey.value);
      if (found?.type === 'string' && !found.searchable && found.values) {
        return found.values;
      }
      return [];
    });

    const addFilter = () => {
      if (selectedFilterType.value === 'number') {
        if (['>', '<', '>=', '<=', '=='].includes(selectedOperator.value)) {
          const filter: NumberComparisonFilter = {
            name: name.value,
            description: description.value,
            key: selectedKey.value,
            operator: selectedOperator.value as ('>' | '<' | '>=' | '<=' | '=='),
            value: value.value as number,
            layers: layers.value,
            type: 'number',
            enabled: false,
            interactable: false,
            userEnabled: true,
          };
          emit('add', filter);
        } else if (selectedOperator.value === 'between') {
          const filter: NumberBetweenFilter = {
            name: name.value,
            description: description.value,
            key: selectedKey.value,
            operator: 'between',
            minValue: rangeValue.value[0],
            maxValue: rangeValue.value[1],
            layers: layers.value,
            type: 'number',
            enabled: false,
            interactable: false,
            userEnabled: true,
          };
          emit('add', filter);
        }
      } else if (selectedFilterType.value === 'string') {
        if (selectedOperator.value === '==') {
          const filter: StringMatchFilter = {
            name: name.value,
            description: description.value,
            key: selectedKey.value,
            operator: '==',
            value: value.value as string,
            layers: layers.value,
            type: 'string',
            enabled: false,
            interactable: false,
            userEnabled: true,
          };
          emit('add', filter);
        } else if (selectedOperator.value === 'contains') {
          const filter: StringContainsFilter = {
            name: name.value,
            description: description.value,
            key: selectedKey.value,
            operator: 'contains',
            value: value.value as string,
            layers: layers.value,
            type: 'string',
            enabled: false,
            interactable: false,
            userEnabled: true,
          };
          emit('add', filter);
        } else if (selectedOperator.value === 'in') {
          const filter: StringInArrayFilter = {
            name: name.value,
            description: description.value,
            key: selectedKey.value,
            operator: 'in',
            values: values.value as string[],
            layers: layers.value,
            type: 'string',
            enabled: false,
            interactable: false,
            userEnabled: true,
          };
          emit('add', filter);
        }
      }
    };

    const cancel = () => {
      emit('cancel');
    };
    return {
      filterTypes,
      selectedFilterType,
      selectedOperator,
      operators,
      availableAttributes,
      selectedKey,
      name,
      description,
      layers,
      rangeValue,
      value,
      values,
      toggleLayerAnnotation,
      cancel,
      addFilter,
      selectedAttributeValue,
      possibleValues,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      Add Filter
    </v-card-title>
    <v-card-text v-if="filterTypes.length === 0">
      <v-alert type="warning">
        Set up properties to use filters
      </v-alert>
    </v-card-text>
    <v-card-text v-else>
      <v-row dense>
        <v-select
          v-model="selectedFilterType"
          label="Filter Type"
          :items="filterTypes"
        />
      </v-row>
      <v-row dense>
        <v-select
          v-model="selectedKey"
          label="Attribute"
          :items="availableAttributes"
          item-title="displayName"
          item-value="key"
        />
      </v-row>
      <v-row dense>
        <v-text-field
          v-model="name"
          label="Name"
        />
        <v-text-field
          v-model="description"
          label="Description"
        />
      </v-row>
      <v-row
        dense
        style="max-width:300px"
        align="center"
        justify="center"
        class="pb-4"
      >
        <b>Layers:</b>
        <v-tooltip text="Line Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="layers.includes('line') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerAnnotation('line')"
            >
              mdi-vector-line
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Polygon Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="layers.includes('fill') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerAnnotation('fill')"
            >
              mdi-pentagon
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Point Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="layers.includes('circle') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerAnnotation('circle')"
            >
              mdi-circle-outline
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Building Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="
                layers.includes('fill-extrusion') ? 'primary' : ''
              "
              size="x-small"
              class="icon-center"
              @click="toggleLayerAnnotation('fill-extrusion')"
            >
              mdi-domain
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Text Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="layers.includes('text') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerAnnotation('text')"
            >
              mdi-format-text
            </v-icon>
          </template>
        </v-tooltip>
      </v-row>
      <v-row dense>
        <v-select
          v-model="selectedOperator"
          :items="operators"
          label="Operator"
        />
      </v-row>
      <div v-if="selectedFilterType === 'number'">
        <v-row dense>
          <v-spacer />
          <v-col>
            <b>Min:</b> <span class="pl-2"> {{ selectedAttributeValue ? selectedAttributeValue.min : 0 }}</span>
          </v-col>
          <v-col>
            <b>Max:</b> <span class="pl-2"> {{ selectedAttributeValue ? selectedAttributeValue.max : 1 }}</span>
          </v-col>
          <v-spacer />
        </v-row>
        <v-row
          v-if="['>', '<', '>=', '<='].includes(selectedOperator)"
          dense
        >
          <v-number-input
            v-model="value"
            density="compact"
            label="number"
            control-variant="split"
          />
        </v-row>
        <v-row
          v-if="'between' === selectedOperator"
          dense
        >
          <v-range-slider
            v-model="rangeValue"
            density="compact"
            step="1"
            height="1"
            thumb-size="5"
            thumb-label="always"
            :min="selectedAttributeValue ? selectedAttributeValue.min : 0 "
            :max="selectedAttributeValue ? selectedAttributeValue.max : 1"
          />
        </v-row>
      </div>
      <div v-if="selectedFilterType === 'string'">
        <v-row
          v-if="['contains', '=='].includes(selectedOperator)"
          dense
        >
          <v-text-field
            v-model="value"
            density="compact"
            label="Value"
          />
        </v-row>
        <v-row
          v-else-if="selectedOperator === 'in'"
          dense
        >
          <v-combobox
            v-model="values"
            chips
            multiple
            label="Values"
            :items="possibleValues"
          />
        </v-row>
      </div>
      <div v-if="selectedFilterType === 'bool'">
        <v-row
          v-if="selectedOperator === '=='"
          dense
        >
          <v-checkbox
            v-model="value"
            label="Value"
          />
        </v-row>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-row dense>
        <v-spacer />
        <v-btn
          color="error"
          @click="cancel()"
        >
          Cancel
        </v-btn>
        <v-btn
          class="ml-2"
          color="success"
          @click="addFilter()"
        >
          Add
        </v-btn>
      </v-row>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.tab {
  border: 1px solid lightgray;
  align-content: center;
}

.tab:hover {
  cursor: pointer;
}
.icon-center {
  width:35px;
  height:35px;
  border: 1px solid lightgray;
  display: flex;
  align-items: center;
  justify-content: center;
}

</style>

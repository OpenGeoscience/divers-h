<!-- eslint-disable vue/max-len -->
<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import { AvailablePropertyDisplay, SearchableVectorData } from '../../../types';
import MapStore from '../../../MapStore';
import VectorFeatureSearchFilterItem from './VectorFeatureSearchFilterItem.vue';

export default defineComponent({
  components: {
    VectorFeatureSearchFilterItem,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const localData: Ref<SearchableVectorData> = ref({
      mainTextSearchFields: [],
      configurableFilters: [],
      display: {
        titleKey: '',
        subtitleKeys: [],
        detailStrings: [],
        sortableFields: [],
        sortable: false,
        hoverHighlight: false,
        geospatialFilterEnabled: false,
        autoOpenSideBar: true,
        zoomButton: false,
        selectionButton: false,
        zoomType: 'level',
        zoomBufferOrLevel: 15,
      },
    });
    const searchDialog = ref(false);
    const availableProperties: Ref<Record<string, AvailablePropertyDisplay>> = ref({});

    const getDisplayName = (key: string) => {
      if (availableProperties.value[key]) {
        return availableProperties.value[key].displayName || key;
      }
      return key;
    };
    const loadInitialData = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found) {
        if (found.default_style.searchableVectorFeatureData) {
          localData.value = found.default_style.searchableVectorFeatureData;
        }
        if (found.default_style.properties?.availableProperties) {
          availableProperties.value = found.default_style.properties.availableProperties;
        }
      }
    };

    const updateVectorFeatureSearch = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found) {
        found.default_style.searchableVectorFeatureData = localData.value;
      }
    };

    onMounted(() => {
      loadInitialData();
    });

    const addKeyDialog = ref(false);
    const addingKeyType: Ref<'detail' | 'subtitle'> = ref('detail');
    const addingKey: Ref<{ key: string, showDisplayName: boolean } | undefined> = ref();
    const availablePropertyKeys = computed(() => Object.keys(availableProperties.value || {}).map((key) => ({
      title: availableProperties.value?.[key]?.displayName || key,
      value: key,
    })));

    const availableTitleKeys = computed(() => Object.keys(availableProperties.value || {}).map((key) => ({ title: getDisplayName(key), value: key })));

    const availableSubtitleKeys = computed(() => Object.keys(availableProperties.value || {}).map((key) => ({
      title: availableProperties.value?.[key]?.displayName || key,
      value: key,
    })).filter((key) => !localData.value.display.subtitleKeys.find((item) => item.key === key.value)));

    const availableDetailKeys = computed(() => Object.keys(availableProperties.value || {}).map((key) => ({
      title: availableProperties.value?.[key]?.displayName || key,
      value: key,
    })).filter((key) => !localData.value.display.detailStrings.find((item) => item.key === key.value)));
    const removeMainTextSearchField = (index: number) => {
      localData.value.mainTextSearchFields?.splice(index, 1);
    };

    const addNewKey = (type: 'detail' | 'subtitle') => {
      addingKeyType.value = type;
      addKeyDialog.value = true;
      addingKey.value = { key: '', showDisplayName: false };
    };

    const saveNewKey = (type: 'detail' | 'subtitle') => {
      if (addingKey.value) {
        if (type === 'detail') {
          localData.value.display.detailStrings.push(
            { key: addingKey.value.key, showDisplayName: addingKey.value.showDisplayName },
          );
        } else {
          localData.value.display.subtitleKeys.push(
            { key: addingKey.value.key, showDisplayName: addingKey.value.showDisplayName },
          );
        }
      }
      addKeyDialog.value = false;
      addingKey.value = undefined;
    };

    const removeKey = (index: number, type: 'detail' | 'subtitle') => {
      if (type === 'detail') {
        localData.value.display.detailStrings.splice(index, 1);
      } else {
        localData.value.display.subtitleKeys.splice(index, 1);
      }
    };

    const saveChanges = () => {
      updateVectorFeatureSearch();
      searchDialog.value = false;
    };

    return {
      localData,
      availablePropertyKeys,
      removeMainTextSearchField,
      removeKey,
      saveChanges,
      addKeyDialog,
      addingKeyType,
      availableTitleKeys,
      availableSubtitleKeys,
      availableDetailKeys,
      addingKey,
      addNewKey,
      saveNewKey,
      searchDialog,
      getDisplayName,
    };
  },
});
</script>addSubtitleKey

<template>
  <v-row dense align="center" justify="center">
    <h3>VectorFeature Searchable</h3>
    <v-spacer />
    <v-icon :disabled="availablePropertyKeys.length === 0" @click="searchDialog = true">
      mdi-cog
    </v-icon>
  </v-row>
  <v-row v-if="availablePropertyKeys.length === 0">
    <v-alert type="warning">
      Properties need to be configured before setting up search fields
    </v-alert>
  </v-row>
  <div v-if="localData && localData.mainTextSearchFields && localData.mainTextSearchFields.length > 0" class="my-1">
    <b class="mr-2">Searchable:</b>
    <v-chip
      v-for="(field, index) in localData.mainTextSearchFields"
      :key="index"
      size="x-small"
    >
      {{ field.title }}
    </v-chip>
  </div>
  <div v-if="localData && localData.display" class="my-1">
    <b class="mr-2">Title:</b>
    <span>{{ getDisplayName(localData.display.titleKey) }}</span>
  </div>
  <div v-if="localData && localData.display" class="my-1">
    <b class="mr-2">Subtitles:</b>
    <v-chip
      v-for="(field, index) in localData.display.subtitleKeys"
      :key="index"
      size="x-small"
    >
      {{ field.key }}
    </v-chip>
  </div>
  <div v-if="localData && localData.display" class="my-1">
    <b class="mr-2">Details:</b>
    <v-chip
      v-for="(field, index) in localData.display.detailStrings"
      :key="index"
      size="x-small"
    >
      {{ field.key }}
    </v-chip>
  </div>

  <v-dialog v-model="searchDialog" width="800px">
    <v-card>
      <v-card-title>Edit Searchable Vector Data</v-card-title>
      <v-card-text>
        <v-expansion-panels>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <strong>Search and Filters</strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-expansion-panels>
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <strong>Main Text Search Fields</strong>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-combobox
                      v-model="localData.mainTextSearchFields"
                      :items="availablePropertyKeys"
                      multiple
                      chips
                      clearable
                      closable-chips
                      item-title="title"
                      item-value="value"
                      label="Select or Add Fields"
                    />
                    <v-switch
                      v-model="localData.display.geospatialFilterEnabled"
                      :color="localData.display.geospatialFilterEnabled ? 'primary' : ''"
                      label="BBox Filter Enabled"
                    />
                    <v-switch
                      v-model="localData.display.selectionButton"
                      :color="localData.display.selectionButton ? 'primary' : ''"
                      label="Selection Button"
                    />
                    <v-switch
                      v-model="localData.display.zoomButton"
                      :color="localData.display.zoomButton ? 'primary' : ''"
                      label="Zoom Button Enabled"
                    />
                    <div v-if="localData.display.zoomButton">
                      <v-text-field v-model.number="localData.display.zoomBufferOrLevel" label="Zoom Level" />
                    </div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <strong>Filters</strong>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <p>Filters will be implmented in the future</p>
                    <VectorFeatureSearchFilterItem
                      v-if="false"
                      v-model="localData.configurableFilters"
                      :available-property-keys="availablePropertyKeys"
                    />
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-expansion-panel-text>
          </v-expansion-panel>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <strong>Display</strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-switch v-model="localData.display.autoOpenSideBar" label="Auto Open Sidebar" />
              <v-expansion-panels>
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <strong>Title</strong>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-select
                      v-model="localData.display.titleKey"
                      :items="availableTitleKeys"
                      item-title="title"
                      item-value="value"
                      label="Title Key"
                    />
                  </v-expansion-panel-text>
                </v-expansion-panel>
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <strong>Subtitle</strong>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list>
                      <v-list-item v-for="(subtitle, index) in localData.display.subtitleKeys" :key="index">
                        {{ subtitle.key }} - Show Display Name: {{ subtitle.showDisplayName }}
                        <v-icon color="error" @click="removeKey(index, 'subtitle')">
                          mdi-delete
                        </v-icon>
                      </v-list-item>
                    </v-list>
                    <v-btn @click="addNewKey('subtitle')">
                      Add Subtitle Key
                    </v-btn>
                  </v-expansion-panel-text>
                </v-expansion-panel>
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <strong>Detail Strings</strong>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <h3>Detail Strings</h3>
                    <v-list>
                      <v-list-item v-for="(detail, index) in localData.display.detailStrings" :key="index">
                        {{ detail.key }} - Show Display Name: {{ detail.showDisplayName }}
                        <v-icon color="error" @click="removeKey(index, 'detail')">
                          mdi-delete
                        </v-icon>
                      </v-list-item>
                    </v-list>
                    <v-btn @click="addNewKey('detail')">
                      Add Detail String
                    </v-btn>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
      <v-card-actions>
        <v-btn color="primary" @click="saveChanges">
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
    <v-dialog v-model="addKeyDialog" width="600">
      <v-card>
        <v-card-title>Add Key</v-card-title>
        <v-card-text>
          <v-select
            v-if="addingKey"
            v-model="addingKey.key"
            :items="addingKeyType === 'subtitle' ? availableSubtitleKeys : availableDetailKeys"
            label="Select Key"
          />
          <v-switch v-if="addingKey" v-model="addingKey.showDisplayName" label="Show Display Name" />
        </v-card-text>
        <v-card-actions>
          <v-row>
            <v-spacer />
            <v-btn color="error" class="ml-2" @click="addKeyDialog = false">
              Cancel
            </v-btn>
            <v-btn color="primary" @click="saveNewKey(addingKeyType)">
              Save
            </v-btn>
          </v-row>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog>
</template>

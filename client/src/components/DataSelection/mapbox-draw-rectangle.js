/* eslint-disable no-use-before-define */
/* eslint-disable default-case */
/* eslint-disable no-multi-assign */
/* eslint-disable consistent-return */
/* eslint-disable prefer-destructuring */
/* eslint-disable no-underscore-dangle */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable func-names */
/* eslint-disable no-plusplus */
/* eslint-disable camelcase */
/* eslint-disable no-param-reassign */
/*!
 * Mapbox GL Draw Rotate Scale Rect Mode
 * Author: Andrey Drykovanov
 * Repository: https://github.com/drykovanov/mapbox-gl-draw-rotate-scale-rect-mode
 * License: ISC License
 * Description: A Mapbox GL JS plugin for adding rotate and scale functionality to the rectangle mode in Mapbox Draw.
 * Modifications: Some minor modifications to work with newer instances of mapbox-gl-draw
 */

import MapboxDraw from '@mapbox/mapbox-gl-draw';

import { lineString, point } from '@turf/helpers';
import bearing from '@turf/bearing';
// import centroid from '@turf/centroid';
import center from '@turf/center';
import midpoint from '@turf/midpoint';
import distance from '@turf/distance';
import destination from '@turf/destination';
import transformRotate from '@turf/transform-rotate';
import transformScale from '@turf/transform-scale';

const Constants = MapboxDraw.constants;
const {
  doubleClickZoom,
  createSupplementaryPoints,
  CommonSelectors,
  moveFeatures,
} = MapboxDraw.lib;

export const TxRectMode = {};

export const TxCenter = {
  Center: 0, // rotate or scale around center of polygon
  Opposite: 1, // rotate or scale around opposite side of polygon
};

function parseTxCenter(value, defaultTxCenter = TxCenter.Center) {
  if (value === undefined || value == null) return defaultTxCenter;

  if (value === TxCenter.Center || value === TxCenter.Opposite) return value;

  if (value === 'center') return TxCenter.Center;

  if (value === 'opposite') return TxCenter.Opposite;

  throw Error(`Invalid TxCenter: ${value}`);
}

/*
    opts = {
        featureId: ...,

        canScale: default true,
        canRotate: default true,
        canResize: default false,

        rotatePivot: default 'center' or 'opposite',
        scaleCenter: default 'center' or 'opposite',

        canSelectFeatures: default true,    // can exit to simple_select mode
    }
 */
TxRectMode.onSetup = function (opts) {
  const featureId = (opts.featureIds && Array.isArray(opts.featureIds) && opts.featureIds.length > 0)
    ? opts.featureIds[0] : opts.featureId;

  const feature = this.getFeature(featureId);

  if (!feature) {
    throw new Error('You must provide a valid featureId to enter tx_poly mode');
  }

  if (feature.type !== Constants.geojsonTypes.POLYGON) {
    throw new TypeError('tx_poly mode can only handle polygons');
  }
  if (feature.coordinates === undefined
        || feature.coordinates.length !== 1
        || feature.coordinates[0].length <= 2) {
    throw new TypeError('tx_poly mode can only handle polygons');
  }

  const state = {
    featureId,
    feature,

    canTrash: opts.canTrash !== undefined ? opts.canTrash : true,

    canScale: opts.canScale !== undefined ? opts.canScale : true,
    canRotate: opts.canRotate !== undefined ? opts.canRotate : true,
    canResize: opts.canResize !== undefined ? opts.canResize : false,

    singleRotationPoint: opts.singleRotationPoint !== undefined ? opts.singleRotationPoint : false,
    rotationPointRadius: opts.rotationPointRadius !== undefined ? opts.rotationPointRadius : 1.0,

    rotatePivot: parseTxCenter(opts.rotatePivot, TxCenter.Center),
    scaleCenter: parseTxCenter(opts.scaleCenter, TxCenter.Center),

    canSelectFeatures: opts.canSelectFeatures !== undefined ? opts.canSelectFeatures : true,
    // selectedFeatureMode: opts.selectedFeatureMode != undefined ? opts.selectedFeatureMode : 'simple_select',

    dragMoveLocation: opts.startPos || null,
    dragMoving: false,
    canDragMove: false,
    selectedCoordPaths: opts.coordPath ? [opts.coordPath] : [],
  };

  if (!(state.canRotate || state.canScale)) {
    // eslint-disable-next-line no-console
    console.warn('Non of canScale or canRotate is true');
  }

  this.setSelectedCoordinates(this.pathsToCoordinates(featureId, state.selectedCoordPaths));
  this.setSelected(featureId);
  doubleClickZoom.disable(this);

  this.setActionableState({
    combineFeatures: false,
    uncombineFeatures: false,
    trash: state.canTrash,
  });

  return state;
};

TxRectMode.createEdgeCenters = function (state, geojson) {
  const { coordinates } = geojson.geometry;
  const featureId = geojson.properties.id;
  const edgeCenters = [];

  const corners = coordinates[0];
  for (let i = 0; i < corners.length - 1; i++) {
    const edgeMidpoint = midpoint(
      point(corners[i]),
      point(corners[i + 1]),
    ).geometry.coordinates;

    edgeCenters.push({
      type: Constants.geojsonTypes.FEATURE,
      properties: {
        meta: 'edge-center',
        parent: featureId,
        coord_path: `${i}`,
      },
      geometry: {
        type: Constants.geojsonTypes.POINT,
        coordinates: edgeMidpoint,
      },
    });
  }

  return edgeCenters;
};

TxRectMode.onEdgeCenter = function (state, e) {
  this.computeAxes(state, state.feature.toGeoJSON());
  this.startDragging(state, e);
  const about = e.featureTarget.properties;
  state.selectedCoordPaths = [about.coord_path];
  state.txMode = TxMode.Scale;
};

TxRectMode.onTouchStart = TxRectMode.onMouseDown = function (state, e) {
  if (isVertex(e)) return this.onVertex(state, e);
  if (isRotatePoint(e)) return this.onRotatePoint(state, e);
  if (e.featureTarget && e.featureTarget.properties.meta === 'edge-center') return this.onEdgeCenter(state, e);
  if (CommonSelectors.isActiveFeature(e)) return this.onFeature(state, e);
};

TxRectMode.dragScalePoint = function (state, e, delta) {
  if (state.scaling === undefined || state.scaling == null) {
    // eslint-disable-next-line no-console
    console.error('state.scaling required');
    return;
  }

  const polygon = state.feature.toGeoJSON();

  const cIdx = this.coordinateIndex(state.selectedCoordPaths);
  const cCenter = state.scaling.centers[cIdx];
  const subcenter = point(cCenter);
  const m1 = point([e.lngLat.lng, e.lngLat.lat]);

  const dist = distance(subcenter, m1, { units: 'meters' });
  let scale = dist / state.scaling.distances[cIdx];

  if (CommonSelectors.isShiftDown(e)) {
    scale = 0.05 * Math.round(scale / 0.05);
  }

  const scaledFeature = transformScale(
    state.scaling.feature0,
    scale,
    {
      origin: cCenter,
      mutate: false,
    },
  );

  state.feature.incomingCoords(scaledFeature.geometry.coordinates);
  this.fireUpdate();
};

TxRectMode.toDisplayFeatures = function (state, geojson, push) {
  if (state.featureId === geojson.properties.id) {
    geojson.properties.active = Constants.activeStates.ACTIVE;
    push(geojson);

    const suppPoints = createSupplementaryPoints(geojson, {
      map: this.map,
      midpoints: false,
      selectedPaths: state.selectedCoordPaths,
    });

    if (state.canScale) {
      this.computeBisectrix(suppPoints);
      suppPoints.forEach(push);
    }

    if (state.canRotate) {
      const rotPoints = this.createRotationPoints(state, geojson, suppPoints);
      rotPoints.forEach(push);
    }
    if (state.canResize) {
      const resizePoints = this.createResizePoints(state, geojson);
      resizePoints.forEach(push);
    }
  } else {
    geojson.properties.active = Constants.activeStates.INACTIVE;
    push(geojson);
  }

  // this.fireActionable(state);
  this.setActionableState({
    combineFeatures: false,
    uncombineFeatures: false,
    trash: state.canTrash,
  });

  // this.fireUpdate();
};

TxRectMode.onStop = function () {
  doubleClickZoom.enable(this);
  this.clearSelectedCoordinates();
};

// TODO why I need this?
TxRectMode.pathsToCoordinates = function (featureId, paths) {
  return paths.map((coord_path) => ({ feature_id: featureId, coord_path }));
};

TxRectMode.createResizePoints = function (state, geojson) {
  const { coordinates } = geojson.geometry;
  const featureId = geojson.properties && geojson.properties.id;

  const resizeWidgets = [];
  const corners = coordinates[0];

  for (let i = 0; i < corners.length - 1; i++) {
    const c1 = corners[i];
    const c2 = corners[(i + 1) % (corners.length - 1)];
    const midpointCoord = midpoint(point(c1), point(c2)).geometry.coordinates;

    resizeWidgets.push({
      type: Constants.geojsonTypes.FEATURE,
      properties: {
        meta: Constants.meta.MIDPOINT,
        parent: featureId,
        lng: midpointCoord[0],
        lat: midpointCoord[1],
        coord_path: `0.${i}`,
      },
      geometry: {
        type: Constants.geojsonTypes.POINT,
        coordinates: midpointCoord,
      },
    });
  }

  return resizeWidgets;
};

TxRectMode.computeBisectrix = function (points) {
  for (let i1 = 0; i1 < points.length; i1++) {
    const i0 = (i1 - 1 + points.length) % points.length;
    const i2 = (i1 + 1) % points.length;
    // console.log('' + i0 + ' -> ' + i1 + ' -> ' + i2);

    const l1 = lineString([points[i0].geometry.coordinates, points[i1].geometry.coordinates]);
    const l2 = lineString([points[i1].geometry.coordinates, points[i2].geometry.coordinates]);
    const a1 = bearing(points[i0].geometry.coordinates, points[i1].geometry.coordinates);
    const a2 = bearing(points[i2].geometry.coordinates, points[i1].geometry.coordinates);
    // console.log('a1 = '  +a1 + ', a2 = ' + a2);

    let a = (a1 + a2) / 2.0;

    if (a < 0.0) a += 360;
    if (a > 360) a -= 360;

    points[i1].properties.heading = a;
  }
};

TxRectMode._createRotationPoint = function (rotationWidgets, featureId, v1, v2, rotCenter, radiusScale) {
  const cR0 = midpoint(v1, v2).geometry.coordinates;
  const heading = bearing(rotCenter, cR0);
  const distance0 = distance(rotCenter, cR0);
  const distance1 = radiusScale * distance0; // TODO depends on map scale
  const cR1 = destination(rotCenter, distance1, heading, {}).geometry.coordinates;

  rotationWidgets.push({
    type: Constants.geojsonTypes.FEATURE,
    properties: {
      meta: Constants.meta.MIDPOINT,
      parent: featureId,
      lng: cR1[0],
      lat: cR1[1],
      coord_path: v1.properties.coord_path,
      heading,
    },
    geometry: {
      type: Constants.geojsonTypes.POINT,
      coordinates: cR1,
    },
  });
};

TxRectMode.createRotationPoints = function (state, geojson, suppPoints) {
  const { type, coordinates } = geojson.geometry;
  const featureId = geojson.properties && geojson.properties.id;

  const rotationWidgets = [];
  if (type !== Constants.geojsonTypes.POLYGON) {
    return;
  }

  const corners = suppPoints.slice(0);
  corners[corners.length] = corners[0];

  let v1 = null;

  const rotCenter = this.computeRotationCenter(state, geojson);

  if (state.singleRotationPoint) {
    this._createRotationPoint(rotationWidgets, featureId, corners[0], corners[1], rotCenter, state.rotationPointRadius);
  } else {
    corners.forEach((v2) => {
      if (v1 != null) {
        this._createRotationPoint(rotationWidgets, featureId, v1, v2, rotCenter, state.rotationPointRadius);
      }

      v1 = v2;
    });
  }

  return rotationWidgets;
};

TxRectMode.startDragging = function (state, e) {
  this.map.dragPan.disable();
  state.canDragMove = true;
  state.dragMoveLocation = e.lngLat;
};

TxRectMode.stopDragging = function (state) {
  this.map.dragPan.enable();
  state.dragMoving = false;
  state.canDragMove = false;
  state.dragMoveLocation = null;
  state.resizing = false;
  state.resizePoint = null;
};

const isResizePoint = CommonSelectors.isOfMetaType(Constants.meta.MIDPOINT);
const isRotatePoint = CommonSelectors.isOfMetaType(Constants.meta.MIDPOINT);
const isVertex = CommonSelectors.isOfMetaType(Constants.meta.VERTEX);

TxRectMode.onTouchStart = TxRectMode.onMouseDown = function (state, e) {
  if (isVertex(e)) return this.onVertex(state, e);
  if (isRotatePoint(e) && TxRectMode.canRotate) return this.onRotatePoint(state, e);
  if (isResizePoint(e)) return this.onResizePoint(state, e);
  if (CommonSelectors.isActiveFeature(e)) return this.onFeature(state, e);
  // if (isMidpoint(e)) return this.onMidpoint(state, e);
};

const TxMode = {
  Scale: 1,
  Rotate: 2,
  Resize: 3,
};

TxRectMode.onResizePoint = function (state, e) {
  const about = e.featureTarget.properties;

  state.resizing = true;
  state.resizePoint = {
    index: about.coord_path, // Index of the corner being dragged
    center: this.computeRotationCenter(state, state.feature.toGeoJSON()).geometry.coordinates, // Center of the box
  };

  this.startDragging(state, e);
};

TxRectMode.onVertex = function (state, e) {
  // console.log('onVertex()');
  // convert internal MapboxDraw feature to valid GeoJSON:
  this.computeAxes(state, state.feature.toGeoJSON());

  this.startDragging(state, e);
  const about = e.featureTarget.properties;
  state.selectedCoordPaths = [about.coord_path];
  state.txMode = TxMode.Scale;
};

TxRectMode.onRotatePoint = function (state, e) {
  // console.log('onRotatePoint()');
  // convert internal MapboxDraw feature to valid GeoJSON:
  this.computeAxes(state, state.feature.toGeoJSON());

  this.startDragging(state, e);
  const about = e.featureTarget.properties;
  state.selectedCoordPaths = [about.coord_path];
  state.txMode = TxMode.Rotate;
};

TxRectMode.onFeature = function (state, e) {
  state.selectedCoordPaths = [];
  this.startDragging(state, e);
};

TxRectMode.coordinateIndex = function (coordPaths) {
  if (coordPaths.length >= 1) {
    const parts = coordPaths[0].split('.');
    return parseInt(parts[parts.length - 1], 10);
  }
  return 0;
};

TxRectMode.computeRotationCenter = function (state, polygon) {
  const center0 = center(polygon);
  return center0;
};

TxRectMode.computeAxes = function (state, polygon) {
  // TODO check min 3 points
  const center0 = this.computeRotationCenter(state, polygon);
  const corners = polygon.geometry.coordinates[0].slice(0);

  const n = corners.length - 1;
  const iHalf = Math.floor(n / 2);

  // var c0 = corners[corners.length - 1];
  // var headings = corners.map((c1) => {
  //     var rotPoint = midpoint(point(c0),point(c1));
  //     var heading = bearing(center0, rotPoint);
  //     c0 = c1;
  //     return heading;
  // });
  // headings = headings.slice(1);

  const rotateCenters = [];
  const headings = [];

  for (let i1 = 0; i1 < n; i1++) {
    let i0 = i1 - 1;
    if (i0 < 0) i0 += n;

    const c0 = corners[i0];
    const c1 = corners[i1];
    const rotPoint = midpoint(point(c0), point(c1));

    let rotCenter = center0;
    if (TxCenter.Opposite === state.rotatePivot) {
      const i3 = (i1 + iHalf) % n; // opposite corner
      let i2 = i3 - 1;
      if (i2 < 0) i2 += n;

      const c2 = corners[i2];
      const c3 = corners[i3];
      rotCenter = midpoint(point(c2), point(c3));
    }

    rotateCenters[i1] = rotCenter.geometry.coordinates;
    headings[i1] = bearing(rotCenter, rotPoint);
  }

  state.rotation = {
    feature0: polygon, // initial feature state
    centers: rotateCenters,
    headings, // rotation start heading for each point
  };

  // compute current distances from centers for scaling

  const scaleCenters = [];
  const distances = [];
  for (let i = 0; i < n; i++) {
    const c1 = corners[i];
    let c0 = center0.geometry.coordinates;
    if (TxCenter.Opposite === state.scaleCenter) {
      const i2 = (i + iHalf) % n; // opposite corner
      c0 = corners[i2];
    }
    scaleCenters[i] = c0;
    distances[i] = distance(point(c0), point(c1), { units: 'meters' });
  }

  // var distances = polygon.geometry.coordinates[0].map((c) =>
  //     turf.distance(center, turf.point(c), { units: 'meters'}) );

  state.scaling = {
    feature0: polygon, // initial feature state
    centers: scaleCenters,
    distances,
  };
};

TxRectMode.onDrag = function (state, e) {
  if (state.canDragMove !== true) return;
  state.dragMoving = true;
  e.originalEvent.stopPropagation();

  const delta = {
    lng: e.lngLat.lng - state.dragMoveLocation.lng,
    lat: e.lngLat.lat - state.dragMoveLocation.lat,
  };
  if (state.selectedCoordPaths.length > 0 && state.txMode) {
    switch (state.txMode) {
      case TxMode.Rotate:
        this.dragRotatePoint(state, e, delta);
        break;
      case TxMode.Scale:
        this.dragScalePoint(state, e, delta);
        break;
      case TxMode.Resize:
        this.dragResizePoint(state, e, delta);
        break;
    }
  } else {
    this.dragFeature(state, e, delta);
  }

  state.dragMoveLocation = e.lngLat;
};

TxRectMode.dragResizePoint = function (state, e, delta) {
  if (!state.resizing || !state.resizePoint) {
    // eslint-disable-next-line no-console
    console.error('Resize state or resize point missing');
    return;
  }

  const polygon = state.feature.toGeoJSON();
  const coordinates = polygon.geometry.coordinates[0];

  const resizePointIndex = state.resizePoint.index;
  const subCenter = state.resizePoint.center;

  const m1 = [e.lngLat.lng, e.lngLat.lat];

  // Compute the new width and height adjustments based on the dragged point
  const dx = m1[0] - subCenter[0];
  const dy = m1[1] - subCenter[1];

  // Adjust the affected corner(s)
  coordinates[resizePointIndex][0] = subCenter[0] + dx;
  coordinates[resizePointIndex][1] = subCenter[1] + dy;

  // Update the other corners to maintain the rectangle's structure
  // const oppositeIndex = (resizePointIndex + 2) % 4;
  // const adjacentIndex1 = (resizePointIndex + 1) % 4;
  // const adjacentIndex2 = (resizePointIndex + 3) % 4;

  // coordinates[adjacentIndex1][0] = coordinates[resizePointIndex][0];
  // coordinates[adjacentIndex2][1] = coordinates[resizePointIndex][1];
  // coordinates[oppositeIndex] = [
  //   coordinates[resizePointIndex][0] + (coordinates[oppositeIndex][0] - center[0]),
  //   coordinates[resizePointIndex][1] + (coordinates[oppositeIndex][1] - center[1]),
  // ];

  // Update the feature's coordinates with the resized rectangle
  state.feature.incomingCoords([coordinates]);

  // Fire the update event to notify listeners
  this.fireUpdate();
};

TxRectMode.dragRotatePoint = function (state, e, delta) {
  // console.log('dragRotateVertex: ' + e.lngLat + ' -> ' + state.dragMoveLocation);

  if (state.rotation === undefined || state.rotation == null) {
    // eslint-disable-next-line no-console
    console.error('state.rotation required');
    return;
  }

  const polygon = state.feature.toGeoJSON();
  const m1 = point([e.lngLat.lng, e.lngLat.lat]);

  const n = state.rotation.centers.length;
  const cIdx = (this.coordinateIndex(state.selectedCoordPaths) + 1) % n;
  // TODO validate cIdx
  const cCenter = state.rotation.centers[cIdx];
  const subcenter = point(cCenter);

  const heading1 = bearing(center, m1);

  const heading0 = state.rotation.headings[cIdx];
  let rotateAngle = heading1 - heading0; // in degrees
  if (CommonSelectors.isShiftDown(e)) {
    rotateAngle = 5.0 * Math.round(rotateAngle / 5.0);
  }

  const rotatedFeature = transformRotate(
    state.rotation.feature0,
    rotateAngle,
    {
      pivot: subcenter,
      mutate: false,
    },
  );

  state.feature.incomingCoords(rotatedFeature.geometry.coordinates);
  // TODO add option for this:
  this.fireUpdate();
};

TxRectMode.dragScalePoint = function (state, e, delta) {
  if (state.scaling === undefined || state.scaling == null) {
    // eslint-disable-next-line no-console
    console.error('state.scaling required');
    return;
  }

  const polygon = state.feature.toGeoJSON();

  const cIdx = this.coordinateIndex(state.selectedCoordPaths);
  // TODO validate cIdx

  const cCenter = state.scaling.centers[cIdx];
  const subcenter = point(cCenter);
  const m1 = point([e.lngLat.lng, e.lngLat.lat]);

  const dist = distance(subcenter, m1, { units: 'meters' });
  let scale = dist / state.scaling.distances[cIdx];

  if (CommonSelectors.isShiftDown(e)) {
    // TODO discrete scaling
    scale = 0.05 * Math.round(scale / 0.05);
  }

  const scaledFeature = transformScale(
    state.scaling.feature0,
    scale,
    {
      origin: cCenter,
      mutate: false,
    },
  );

  state.feature.incomingCoords(scaledFeature.geometry.coordinates);
  // TODO add option for this:
  this.fireUpdate();
};

TxRectMode.dragFeature = function (state, e, delta) {
  moveFeatures(this.getSelected(), delta);
  state.dragMoveLocation = e.lngLat;
  // TODO add option for this:
  this.fireUpdate();
};

TxRectMode.fireUpdate = function () {
  this.map.fire(Constants.events.UPDATE, {
    action: Constants.updateActions.CHANGE_COORDINATES,
    features: this.getSelected().map((f) => f.toGeoJSON()),
  });
};

TxRectMode.onMouseOut = function (state) {
  // As soon as you mouse leaves the canvas, update the feature
  if (state.dragMoving) {
    this.fireUpdate();
  }
};

TxRectMode.onTouchEnd = TxRectMode.onMouseUp = function (state) {
  if (state.dragMoving) {
    this.fireUpdate();
  }
  this.stopDragging(state);
};

TxRectMode.clickActiveFeature = function (state) {
  state.selectedCoordPaths = [];
  this.clearSelectedCoordinates();
  state.feature.changed();
};

TxRectMode.onClick = function (state, e) {
  if (CommonSelectors.noTarget(e)) return this.clickNoTarget(state, e);
  if (CommonSelectors.isActiveFeature(e)) return this.clickActiveFeature(state, e);
  if (CommonSelectors.isInactiveFeature(e)) return this.clickInactive(state, e);
  this.stopDragging(state);
};

TxRectMode.clickNoTarget = function (state, e) {
  if (state.canSelectFeatures) this.changeMode(Constants.modes.SIMPLE_SELECT);
};

TxRectMode.clickInactive = function (state, e) {
  if (state.canSelectFeatures) {
    this.changeMode(Constants.modes.SIMPLE_SELECT, {
      featureIds: [e.featureTarget.properties.id],
    });
  }
};

TxRectMode.onTrash = function () {
  // TODO check state.canTrash
  this.deleteFeature(this.getSelectedIds());
  // this.fireActionable();
};

export const drawStyle = [
  {
    id: 'gl-draw-polygon-fill-inactive',
    type: 'fill',
    filter: ['all',
      ['==', 'active', 'false'],
      ['==', '$type', 'Polygon'],
      ['!=', 'user_type', 'overlay'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'fill-color': '#3bb2d0',
      'fill-outline-color': '#3bb2d0',
      'fill-opacity': 0.7,
    },
  },
  {
    id: 'gl-draw-polygon-fill-active',
    type: 'fill',
    filter: ['all',
      ['==', 'active', 'true'],
      ['==', '$type', 'Polygon'],
      ['!=', 'user_type', 'overlay'],
    ],
    paint: {
      'fill-color': '#fbb03b',
      'fill-outline-color': '#fbb03b',
      'fill-opacity': 0.7,
    },
  },

  {
    id: 'gl-draw-overlay-polygon-fill-inactive',
    type: 'fill',
    filter: ['all',
      ['==', 'active', 'false'],
      ['==', '$type', 'Polygon'],
      ['==', 'user_type', 'overlay'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'fill-color': '#3bb2d0',
      'fill-outline-color': '#3bb2d0',
      'fill-opacity': 0.01,
    },
  },
  {
    id: 'gl-draw-overlay-polygon-fill-active',
    type: 'fill',
    filter: ['all',
      ['==', 'active', 'true'],
      ['==', '$type', 'Polygon'],
      ['==', 'user_type', 'overlay'],
    ],
    paint: {
      'fill-color': '#fbb03b',
      'fill-outline-color': '#fbb03b',
      'fill-opacity': 0.01,
    },
  },

  {
    id: 'gl-draw-polygon-stroke-inactive',
    type: 'line',
    filter: ['all',
      ['==', 'active', 'false'],
      ['==', '$type', 'Polygon'],
      ['!=', 'user_type', 'overlay'],
      ['!=', 'mode', 'static'],
    ],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#3bb2d0',
      'line-width': 2,
    },
  },

  {
    id: 'gl-draw-polygon-stroke-active',
    type: 'line',
    filter: ['all',
      ['==', 'active', 'true'],
      ['==', '$type', 'Polygon'],
    ],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#fbb03b',
      'line-dasharray': [0.2, 2],
      'line-width': 2,
    },
  },

  // {
  //     'id': 'gl-draw-polygon-midpoint',
  //     'type': 'circle',
  //     'filter': ['all',
  //         ['==', '$type', 'Point'],
  //         ['==', 'meta', 'midpoint']],
  //     'paint': {
  //         'circle-radius': 3,
  //         'circle-color': '#fbb03b'
  //     }
  // },

  {
    id: 'gl-draw-line-inactive',
    type: 'line',
    filter: ['all',
      ['==', 'active', 'false'],
      ['==', '$type', 'LineString'],
      ['!=', 'mode', 'static'],
    ],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#3bb2d0',
      'line-width': 2,
    },
  },
  {
    id: 'gl-draw-line-active',
    type: 'line',
    filter: ['all',
      ['==', '$type', 'LineString'],
      ['==', 'active', 'true'],
    ],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#fbb03b',
      'line-dasharray': [0.2, 2],
      'line-width': 2,
    },
  },
  {
    id: 'gl-draw-polygon-and-line-vertex-stroke-inactive',
    type: 'circle',
    filter: ['all',
      ['==', 'meta', 'vertex'],
      ['==', '$type', 'Point'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'circle-radius': 4,
      'circle-color': '#fff',
    },
  },
  {
    id: 'gl-draw-polygon-and-line-vertex-inactive',
    type: 'circle',
    filter: ['all',
      ['==', 'meta', 'vertex'],
      ['==', '$type', 'Point'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'circle-radius': 2,
      'circle-color': '#fbb03b',
    },
  },

  {
    id: 'gl-draw-polygon-and-line-vertex-scale-icon',
    type: 'symbol',
    filter: ['all',
      ['==', 'meta', 'vertex'],
      ['==', '$type', 'Point'],
      ['!=', 'mode', 'static'],
      ['has', 'heading'],
    ],
    layout: {
      'icon-image': 'scale',
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
      'icon-rotation-alignment': 'map',
      'icon-rotate': ['get', 'heading'],
    },
    paint: {
      'icon-opacity': 1.0,
      'icon-opacity-transition': {
        delay: 0,
        duration: 0,
      },
    },
  },

  {
    id: 'gl-draw-point-point-stroke-inactive',
    type: 'circle',
    filter: ['all',
      ['==', 'active', 'false'],
      ['==', '$type', 'Point'],
      ['==', 'meta', 'feature'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'circle-radius': 5,
      'circle-opacity': 1,
      'circle-color': '#fff',
    },
  },
  {
    id: 'gl-draw-point-inactive',
    type: 'circle',
    filter: ['all',
      ['==', 'active', 'false'],
      ['==', '$type', 'Point'],
      ['==', 'meta', 'feature'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'circle-radius': 3,
      'circle-color': '#3bb2d0',
    },
  },
  {
    id: 'gl-draw-point-stroke-active',
    type: 'circle',
    filter: ['all',
      ['==', '$type', 'Point'],
      ['==', 'active', 'true'],
      ['!=', 'meta', 'midpoint'],
    ],
    paint: {
      'circle-radius': 4,
      'circle-color': '#fff',
    },
  },
  {
    id: 'gl-draw-point-active',
    type: 'circle',
    filter: ['all',
      ['==', '$type', 'Point'],
      ['!=', 'meta', 'midpoint'],
      ['==', 'active', 'true']],
    paint: {
      'circle-radius': 2,
      'circle-color': '#fbb03b',
    },
  },
  {
    id: 'gl-draw-polygon-fill-static',
    type: 'fill',
    filter: ['all', ['==', 'mode', 'static'], ['==', '$type', 'Polygon']],
    paint: {
      'fill-color': '#404040',
      'fill-outline-color': '#404040',
      'fill-opacity': 0.1,
    },
  },
  {
    id: 'gl-draw-polygon-stroke-static',
    type: 'line',
    filter: ['all', ['==', 'mode', 'static'], ['==', '$type', 'Polygon']],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#404040',
      'line-width': 2,
    },
  },
  {
    id: 'gl-draw-line-static',
    type: 'line',
    filter: ['all', ['==', 'mode', 'static'], ['==', '$type', 'LineString']],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#404040',
      'line-width': 2,
    },
  },
  {
    id: 'gl-draw-point-static',
    type: 'circle',
    filter: ['all', ['==', 'mode', 'static'], ['==', '$type', 'Point']],
    paint: {
      'circle-radius': 5,
      'circle-color': '#404040',
    },
  },

  // {
  //     'id': 'gl-draw-polygon-rotate-point',
  //     'type': 'circle',
  //     'filter': ['all',
  //         ['==', '$type', 'Point'],
  //         ['==', 'meta', 'rotate_point']],
  //     'paint': {
  //         'circle-radius': 5,
  //         'circle-color': '#fbb03b'
  //     }
  // },

  {
    id: 'gl-draw-line-rotate-point',
    type: 'line',
    filter: ['all',
      ['==', 'meta', 'midpoint'],
      ['==', '$type', 'LineString'],
      ['!=', 'mode', 'static'],
      // ['==', 'active', 'true']
    ],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#fbb03b',
      'line-dasharray': [0.2, 2],
      'line-width': 2,
    },
  },
  {
    id: 'gl-draw-polygon-rotate-point-stroke',
    type: 'circle',
    filter: ['all',
      ['==', 'meta', 'midpoint'],
      ['==', '$type', 'Point'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'circle-radius': 4,
      'circle-color': '#fff',
    },
  },
  {
    id: 'gl-draw-polygon-rotate-point',
    type: 'circle',
    filter: ['all',
      ['==', 'meta', 'midpoint'],
      ['==', '$type', 'Point'],
      ['!=', 'mode', 'static'],
    ],
    paint: {
      'circle-radius': 2,
      'circle-color': '#fbb03b',
    },
  },
  {
    id: 'gl-draw-polygon-rotate-point-icon',
    type: 'symbol',
    filter: ['all',
      ['==', 'meta', 'midpoint'],
      ['==', '$type', 'Point'],
      ['!=', 'mode', 'static'],
    ],
    layout: {
      'icon-image': 'rotate',
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
      'icon-rotation-alignment': 'map',
      'icon-rotate': ['get', 'heading'],
    },
    paint: {
      'icon-opacity': 1.0,
      'icon-opacity-transition': {
        delay: 0,
        duration: 0,
      },
    },
  },
];

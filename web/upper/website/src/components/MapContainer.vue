<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";
import { Plus, Minus, Aim, FullScreen, Close } from '@element-plus/icons-vue'

// 定义 props 接口, 从父组件接收坐标数据
const props = defineProps({
  lineArr: { type: Array, required: true },      // 轨迹坐标数组
  initialCenter: { type: Array, required: true }, // 初始中心点
  zoom: { type: Number, default: 5 },             // 地图缩放级别
  viewMode: { type: String, default: "3D" },      // 视图模式
  angle: { type: Number, default: 0 },            // 车辆角度
  vehicleSpeed: { type: Number, default: 0 },     // 车辆速度
  altitude: { type: Number, default: 0 }          // 海拔高度
});

// 响应式地图相关实例
const map = ref(null);         // 地图实例
const marker = ref(null);      // 车辆标记
const polyline = ref(null);    // 行驶路线

// 控制面板状态
const showVehicleInfo = ref(false)
const showTrajectory = ref(true)
const showVehicle = ref(true)
const showSatellite = ref(false)

// 当前位置信息
const currentPosition = computed(() => {
  if (props.initialCenter && props.initialCenter.length > 0) {
    const pos = Array.isArray(props.initialCenter[0]) ? props.initialCenter[0] : props.initialCenter
    return {
      lng: pos[0],
      lat: pos[1]
    }
  }
  return { lng: 0, lat: 0 }
})

// 地图控制方法
const switchViewMode = (mode) => {
  if (map.value) {
    map.value.setViewMode(mode)
  }
}

const centerToVehicle = () => {
  if (map.value && currentPosition.value.lng && currentPosition.value.lat) {
    map.value.setCenter([currentPosition.value.lng, currentPosition.value.lat])
    map.value.setZoom(18)
    showVehicleInfo.value = true
  }
}

const fitToTrack = () => {
  if (map.value && polyline.value && props.lineArr.length > 0) {
    map.value.setFitView([polyline.value])
  }
}

const zoomIn = () => {
  if (map.value) {
    map.value.zoomIn()
  }
}

const zoomOut = () => {
  if (map.value) {
    map.value.zoomOut()
  }
}

// 图层控制
const toggleTrajectory = () => {
  if (polyline.value) {
    if (showTrajectory.value) {
      map.value.add(polyline.value)
    } else {
      map.value.remove(polyline.value)
    }
  }
}

const toggleVehicle = () => {
  if (marker.value) {
    if (showVehicle.value) {
      map.value.add(marker.value)
    } else {
      map.value.remove(marker.value)
    }
  }
}

const toggleSatellite = () => {
  if (map.value) {
    if (showSatellite.value) {
      map.value.setMapStyle('amap://styles/satellite')
    } else {
      map.value.setMapStyle('amap://styles/normal')
    }
  }
}

// 更新标记和中心点的方法（可暴露给父组件使用）
const updateMarker = (lng, lat) => {
  if (!map.value) return;

  // 1. 移除旧标记
  if (marker.value) {
    map.value.remove(marker.value);
  }

  // 2. 创建新标记
  marker.value = new AMap.Marker({
    position: new AMap.LngLat(lng, lat),
    title: [lng, lat],
    offset: new AMap.Pixel(-26, -15),
    autoRotation: true,
    angle: props.angle,
    icon: new AMap.Icon({
      image: 'data:image/svg+xml;base64,' + btoa(`
        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="#00ffff" opacity="0.3"/>
          <circle cx="20" cy="20" r="12" fill="#00ffff" opacity="0.8"/>
          <circle cx="20" cy="20" r="6" fill="#ffffff"/>
          <polygon points="20,8 24,16 20,14 16,16" fill="#ffffff"/>
        </svg>
      `),
      size: new AMap.Size(40, 40),
      imageOffset: new AMap.Pixel(0, 0)
    })
  });

  // 3. 添加标记到地图
  if (showVehicle.value) {
    map.value.add(marker.value);
  }

  // 4. 添加点击事件
  marker.value.on('click', () => {
    showVehicleInfo.value = true
  })
};

// 初始化地图及组件
const initMap = async (AMap) => {
  map.value = new AMap.Map("container", {
    viewMode: props.viewMode,
    zoom: props.zoom,
    center: props.initialCenter,
    mapStyle: 'amap://styles/normal',
    features: ['bg', 'road', 'building', 'point']
  });

  // 2. 添加车辆标记
  const initialPos = Array.isArray(props.initialCenter[0]) ? props.initialCenter[0] : props.initialCenter
  updateMarker(initialPos[0], initialPos[1])

  // 3. 绘制路线
  initPolylines(AMap);

  // 4. 添加地图事件
  map.value.on('click', () => {
    showVehicleInfo.value = false
  })
};

// 绘制轨迹路线
const initPolylines = (AMap) => {
  // 行驶路线
  polyline.value = new AMap.Polyline({
    path: props.lineArr,
    strokeColor: "#00ff88",
    strokeWeight: 4,
    strokeOpacity: 0.8,
    strokeStyle: 'solid',
    strokeDasharray: [0, 0],
    lineJoin: 'round',
    lineCap: 'round'
  });
  
  if (showTrajectory.value) {
    map.value.add(polyline.value);
  }
  
  // 自动调整视野
  if (props.lineArr.length > 0) {
    map.value.setFitView([polyline.value]);
  }
};

// 监听 lineArr 变化重新绘制路线
watch(() => props.lineArr, (newPath) => {
  if (polyline.value && newPath.length > 0) {
    polyline.value.setPath(newPath);
    if (showTrajectory.value) {
      map.value.setFitView([polyline.value]);
    }
  }
});

// 监听 initialCenter 变化重置中心点和车子标记
watch(() => props.initialCenter, (newCenter) => {
  if (map.value && marker.value && newCenter.length > 0) {
    const pos = Array.isArray(newCenter[0]) ? newCenter[0] : newCenter
    updateMarker(pos[0], pos[1])
    marker.value.setTitle(`${pos[0]}, ${pos[1]}`)
  }
});

// 监听角度变化
watch(() => props.angle, (newAngle) => {
  if (marker.value) {
    marker.value.setAngle(newAngle);
  }
});

// 生命周期钩子
onMounted(() => {
  AMapLoader.load({
    key: "5453af1e113023d3770919da5ce11f23",
    version: "2.0",
    plugins: ["AMap.Marker", "AMap.Polyline", "AMap.Icon"]
  })
    .then((AMap) => {
      initMap(AMap);
    })
    .catch((error) => {
      console.error("AMap load failed:", error);
    });
});

// 组件卸载时清理
onUnmounted(() => {
  if (map.value) {
    map.value.destroy(); // 销毁地图实例
    map.value = null;
  }
});
</script>

<template>
  <div class="map-wrapper">
    <div id="container" class="map-container"></div>
    
    <!-- 地图控制面板 -->
    <div class="map-controls">
      <div class="control-group">
        <el-button-group>
          <el-button 
            size="small" 
            :type="viewMode === '2D' ? 'primary' : ''"
            @click="switchViewMode('2D')"
          >
            2D
          </el-button>
          <el-button 
            size="small" 
            :type="viewMode === '3D' ? 'primary' : ''"
            @click="switchViewMode('3D')"
          >
            3D
          </el-button>
        </el-button-group>
      </div>
      
      <div class="control-group">
        <el-button size="small" @click="centerToVehicle" :icon="Aim">定位车辆</el-button>
        <el-button size="small" @click="fitToTrack" :icon="FullScreen">适合轨迹</el-button>
      </div>
      
      <div class="control-group zoom-controls">
        <el-button size="small" @click="zoomIn" :icon="Plus"></el-button>
        <el-button size="small" @click="zoomOut" :icon="Minus"></el-button>
      </div>
    </div>
    
    <!-- 车辆信息面板 -->
    <div class="vehicle-info-panel" v-if="showVehicleInfo">
      <div class="info-header">
        <h4>车辆状态</h4>
        <el-button size="small" text @click="showVehicleInfo = false" :icon="Close"></el-button>
      </div>
      <div class="info-content">
        <div class="info-item">
          <span class="label">坐标:</span>
          <span class="value">{{ currentPosition.lng?.toFixed(6) }}, {{ currentPosition.lat?.toFixed(6) }}</span>
        </div>
        <div class="info-item">
          <span class="label">方向:</span>
          <span class="value">{{ angle }}°</span>
        </div>
        <div class="info-item">
          <span class="label">速度:</span>
          <span class="value">{{ vehicleSpeed }} km/h</span>
        </div>
        <div class="info-item">
          <span class="label">海拔:</span>
          <span class="value">{{ altitude }} m</span>
        </div>
      </div>
    </div>
    
    <!-- 图层控制面板 -->
    <div class="layer-control">
      <el-checkbox v-model="showTrajectory" @change="toggleTrajectory">显示轨迹</el-checkbox>
      <el-checkbox v-model="showVehicle" @change="toggleVehicle">显示车辆</el-checkbox>
      <el-checkbox v-model="showSatellite" @change="toggleSatellite">卫星图层</el-checkbox>
    </div>
  </div>
</template>

<style scoped>
.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 10px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
  border-radius: 10px;
}

/* 地图控制面板 */
.map-controls {
  position: absolute;
  top: 15px;
  right: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 10;
}

.control-group {
  display: flex;
  gap: 5px;
  background: rgba(12, 20, 38, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 8px;
  padding: 5px;
}

.zoom-controls {
  flex-direction: column;
}

.control-group .el-button {
  --el-button-bg-color: transparent;
  --el-button-border-color: rgba(0, 255, 255, 0.3);
  --el-button-text-color: #b8c5d6;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.control-group .el-button:hover {
  --el-button-bg-color: rgba(0, 255, 255, 0.1);
  --el-button-border-color: rgba(0, 255, 255, 0.6);
  --el-button-text-color: #00ffff;
  transform: scale(1.05);
}

.control-group .el-button--primary {
  --el-button-bg-color: rgba(0, 255, 255, 0.2);
  --el-button-border-color: #00ffff;
  --el-button-text-color: #00ffff;
}

/* 车辆信息面板 */
.vehicle-info-panel {
  position: absolute;
  bottom: 15px;
  left: 15px;
  background: rgba(12, 20, 38, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 10px;
  padding: 15px;
  min-width: 250px;
  z-index: 10;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.2);
  padding-bottom: 8px;
}

.info-header h4 {
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  text-shadow: 0 0 5px rgba(0, 255, 255, 0.3);
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-item .label {
  color: #b8c5d6;
  font-size: 14px;
  font-weight: 500;
}

.info-item .value {
  color: #00ffff;
  font-size: 14px;
  font-weight: 600;
  font-family: 'Courier New', monospace;
  text-shadow: 0 0 3px rgba(0, 255, 255, 0.3);
}

/* 图层控制面板 */
.layer-control {
  position: absolute;
  top: 15px;
  left: 15px;
  background: rgba(12, 20, 38, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 10;
}

.layer-control :deep(.el-checkbox) {
  margin-right: 0;
}

.layer-control :deep(.el-checkbox__label) {
  color: #b8c5d6;
  font-size: 12px;
}

.layer-control :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #00ffff;
  border-color: #00ffff;
}

.layer-control :deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
  color: #00ffff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .map-controls {
    top: 10px;
    right: 10px;
  }
  
  .control-group {
    padding: 3px;
  }
  
  .vehicle-info-panel {
    bottom: 10px;
    left: 10px;
    right: 10px;
    min-width: auto;
    padding: 12px;
  }
  
  .layer-control {
    top: 10px;
    left: 10px;
    padding: 8px;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  
  .info-item .value {
    font-size: 12px;
  }
}

/* 动画效果 */
.vehicle-info-panel,
.map-controls,
.layer-control {
  animation: slideInPanel 0.3s ease-out;
}

@keyframes slideInPanel {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

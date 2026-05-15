<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import MapContainer from '../components/MapContainer.vue'
import NavBarNew from '../components/NavBarNew.vue'
import CyberInfoCard from '../components/CyberInfoCard.vue'
import { useAxiosStore } from '../stores/axios'
import { usePacketStore } from '../stores/dataPacket'
import { MapLocation, TrendCharts } from '@element-plus/icons-vue'

const axiosStore = useAxiosStore()
const packetStore = usePacketStore()

const now = ref(Date.now())
const appStartTime = Date.now()
let timer = null

// 地图配置
packetStore.raw_data_get(axiosStore.responseData)
const dynamicLineArr = packetStore.map_data_process()
const currentCenter = ref([81.312141132393, 40.55683301927755])
const mapConfig = { zoom: 18, mode: '3D' }

const latestGpsData = computed(() => {
  return axiosStore.responseData.slice(-1)[0] || {}
})

const batteryPercentage = computed(() => {
  const status = axiosStore.vehicleStatus || {}
  if (typeof status.battery_percentage === 'number') {
    return Math.min(Math.max(status.battery_percentage, 0), 100)
  }

  const voltage = Number(status.battery_voltage || 0)
  if (voltage <= 0) {
    return 0
  }

  return Math.min(Math.max(((voltage - 10.5) / (12.6 - 10.5)) * 100, 0), 100)
})

const workingTime = computed(() => {
  const elapsed = Math.max(0, Math.floor((now.value - appStartTime) / 1000))
  const hours = String(Math.floor(elapsed / 3600)).padStart(2, '0')
  const minutes = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0')
  const seconds = String(elapsed % 60).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
})

const gpsLocationText = computed(() => {
  const location = latestGpsData.value?.location
  if (!Array.isArray(location) || location.length !== 2) {
    return '--'
  }
  return `${Number(location[0]).toFixed(6)}, ${Number(location[1]).toFixed(6)}`
})

const refreshData = () => {
  now.value = Date.now()
  return Promise.all([
    axiosStore.getData(),
    axiosStore.getVehicleStatus()
  ]).then(() => {
    packetStore.raw_data_get(axiosStore.responseData)
    packetStore.map_data_process()
    const latestPoint = dynamicLineArr.value.slice(-1)[0]
    if (latestPoint) {
      currentCenter.value = latestPoint
    }
  })
}

onMounted(() => {
  refreshData()
  timer = setInterval(refreshData, 2000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  timer = null
})
</script>

<template>
  <NavBarNew />

  <div class="main-page">
    <div class="status-overview">
      <div class="status-grid">
        <CyberInfoCard
          title="通信状态"
          :value="axiosStore.connectStatus ? '正常连接' : '连接中断'"
          emoji="📡"
          :type="axiosStore.connectStatus ? 'success' : 'danger'"
          :status="axiosStore.connectStatus ? 'online' : 'offline'"
          :is-pulse="!axiosStore.connectStatus"
        />

        <CyberInfoCard
          title="数据包统计"
          :value="`${packetStore.dataCount} 条`"
          emoji="📊"
          type="info"
          subtitle="实时更新"
        />

        <CyberInfoCard
          title="电池电量"
          :value="`${Math.round(batteryPercentage)}%`"
          emoji="⚡"
          :type="batteryPercentage > 50 ? 'success' : 'warning'"
          :show-progress="true"
          :progress-value="batteryPercentage"
        />

        <CyberInfoCard
          title="工作时间"
          :value="workingTime"
          emoji="⏱️"
          type="primary"
          subtitle="持续运行"
        />
      </div>
    </div>

    <div class="monitor-content">
      <div class="cyber-card map-panel">
        <div class="card-header">
          <div class="header-icon">
            <el-icon><MapLocation /></el-icon>
          </div>
          <div>
            <h2>实时轨迹监控</h2>
            <p class="header-subtitle">当前坐标：{{ gpsLocationText }}</p>
          </div>
          <div class="map-controls">
            <el-button-group size="small">
              <el-button :icon="TrendCharts">2D</el-button>
              <el-button :icon="TrendCharts" type="primary">3D</el-button>
            </el-button-group>
          </div>
          <div class="header-glow"></div>
        </div>
        <div class="map-content">
          <MapContainer
            :line-arr="dynamicLineArr"
            :initial-center="currentCenter"
            :zoom="mapConfig.zoom"
            :view-mode="mapConfig.mode"
            :angle="latestGpsData?.angle || 0"
            :vehicle-speed="latestGpsData?.speed || 0"
            :altitude="latestGpsData?.altitude || 900"
          />
        </div>
      </div>

      <div class="cyber-card ai-panel">
        <div class="card-header">
          <div class="header-icon">🤖</div>
          <h2>智能问答助手</h2>
          <div class="header-glow"></div>
        </div>
        <div class="ai-content">
          <iframe
            src="http://127.0.0.1:8080/ui/chat/a668fc74f5f490f1"
            class="ai-iframe"
            frameborder="0"
            allow="microphone">
          </iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.main-page {
  padding-top: 70px;
  min-height: 100vh;
  background: transparent;
}

.status-overview {
  padding: 20px;
  margin-bottom: 20px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.monitor-content {
  display: grid;
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px 20px;
}

.cyber-card {
  background: rgba(12, 20, 38, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 15px;
  overflow: hidden;
  margin-bottom: 20px;
  transition: all 0.3s ease;
  position: relative;
}

.cyber-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #00ffff, #00ff88);
  opacity: 0.8;
}

.cyber-card:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 255, 255, 0.5);
  box-shadow: 0 15px 40px rgba(0, 255, 255, 0.2);
}

.card-header {
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(0, 255, 255, 0.2);
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}

.header-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 255, 255, 0.1);
  border-radius: 10px;
  color: #00ffff;
  font-size: 1.5rem;
}

.card-header h2 {
  color: #ffffff;
  font-size: 1.3rem;
  font-weight: 700;
  margin: 0;
  text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
}

.header-subtitle {
  margin: 4px 0 0;
  color: #7a8699;
  font-size: 0.85rem;
}

.header-glow {
  position: absolute;
  top: 0;
  right: 0;
  width: 100px;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.1));
  pointer-events: none;
}

.map-panel {
  height: calc(100vh - 230px);
  min-height: 560px;
}

.map-controls {
  margin-left: auto;
}

.map-content {
  height: calc(100% - 88px);
}

.ai-content {
  height: 400px;
  padding: 0;
}

.ai-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 0 0 15px 15px;
}

@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }

  .status-overview {
    padding: 10px;
  }

  .monitor-content {
    padding: 0 10px 20px;
  }

  .card-header {
    padding: 15px;
    align-items: flex-start;
  }

  .map-controls {
    display: none;
  }

  .map-panel {
    height: 70vh;
    min-height: 480px;
  }
}
</style>

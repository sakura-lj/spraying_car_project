<script setup>

import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import MapContainer from '../components/MapContainer.vue'
import NavBarNew from '../components/NavBarNew.vue'
import CyberInfoCard from '../components/CyberInfoCard.vue'
import { useAxiosStore } from "../stores/axios"
import { usePacketStore } from '../stores/dataPacket'
import { ElMessage } from 'element-plus'
import { Check, Close, Operation, Monitor, MapLocation, VideoPlay, VideoPause, 
         TrendCharts, Setting, Connection } from '@element-plus/icons-vue'

const axiosStore = useAxiosStore()
const packetStore = usePacketStore()

const statusValue = ref(false)
const speedValue = ref(51)
const turnPosition = ref(51)
const now = ref(Date.now())
const appStartTime = Date.now()

// 定时器
let timer = null

// 地图配置
// 动态数据源
packetStore.raw_data_get(axiosStore.responseData) // 先获取一次初始值如何呢？
const dynamicLineArr = packetStore.map_data_process(); // 是不是初始化的时候为空
const currentCenter = ref([81.312141132393, 40.55683301927755]);
const mapConfig = { zoom: 18, mode: "3D" };

const latestGpsData = computed(() => {
  return axiosStore.responseData.slice(-1)[0] || {}
})

const speedPercentage = computed(() => {
  const speed = Number(latestGpsData.value?.speed || 0)
  return Math.min((speed / 5) * 100, 100) // 假设最大车速5m/s
})

const pumpRunning = computed(() => {
  return Boolean(axiosStore.vehicleStatus?.spray_state || latestGpsData.value?.pump_status?.pump1)
})

const pumpStatusColor = computed(() => {
  return pumpRunning.value ? 'success' : 'danger'
})

const pumpStatusText = computed(() => {
  return pumpRunning.value ? '运行' : '停止'
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

// 监控model值， 然后给status路由发送状态
watch(statusValue, (value)=>{
  axiosStore.statusPost(value)
  if (value) {
    refreshData()
  }
})

// 控制功能
const startSpray = () => {
  sendControlCommand('/spray_control', { state: true }, '喷药功能已启动', '喷药启动失败')
}

const stopSpray = () => {
  sendControlCommand('/spray_control', { state: false }, '喷药功能已停止', '喷药停止失败')
}

const applySpeed = () => {
  sendControlCommand('/speed_control', { speed: speedValue.value }, `速度已设置为 ${speedValue.value}`, '速度设置失败')
}

const setDirection = (direction) => {
  const directionText = ['停止', '前进', '后退'][direction] || '停止'
  sendControlCommand('/direction_control', { direction }, `方向已切换为${directionText}`, '方向控制失败')
}

const applyTurn = () => {
  sendControlCommand('/turn_control', { position: turnPosition.value }, `转向位置已设置为 ${turnPosition.value}`, '转向设置失败')
}

const emergencyStop = () => {
  axios.post('/emergency_stop', {})
    .then((response) => {
      const data = response.data || {}
      if (data.success) {
        ElMessage.warning(data.message || '紧急停止命令执行完成')
      } else {
        ElMessage.error(data.message || '紧急停止执行不完整')
      }
      axiosStore.getVehicleStatus()
    })
    .catch((error) => {
      const message = error.response?.data?.message || error.message || '紧急停止失败'
      ElMessage.error(`紧急停止失败: ${message}`)
    })
}

const sendControlCommand = (url, payload, successText, errorText) => {
  axios.post(url, payload)
    .then((response) => {
      const data = response.data || {}
      if (data.success) {
        ElMessage.success(data.message || successText)
      } else {
        ElMessage.error(data.message || errorText)
      }
      axiosStore.getVehicleStatus()
    })
    .catch((error) => {
      const message = error.response?.data?.message || error.message || errorText
      ElMessage.error(`${errorText}: ${message}`)
    })
}

onMounted(() => {
  // 初始刷新
  refreshData()
  // 避免刷新之后不清除数据
  axiosStore.statusPost(false)
  // 每2s刷新车辆状态，运行中同步刷新GPS轨迹
  timer = setInterval(() => {
    now.value = Date.now()
    axiosStore.getVehicleStatus()
    if(statusValue.value){
      refreshData()
    }
  }, 2000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  timer = null
})

</script>

<template>
  <!-- 导航栏 -->
  <NavBarNew />
  
  <div class="main-page">
    <!-- 状态栏 -->
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

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <!-- 设备控制卡片 -->
        <div class="cyber-card control-panel">
          <div class="card-header">
            <div class="header-icon">
              <el-icon><Operation /></el-icon>
            </div>
            <h2>设备控制台</h2>
            <div class="header-glow"></div>
          </div>
          
          <div class="control-content">
            <!-- 主控开关 -->
            <div class="main-switch">
              <el-switch
                v-model="statusValue"
                size="large"
                inline-prompt
                active-text="运行中"
                inactive-text="已停止"
                :active-icon="Check"
                :inactive-icon="Close"
                style="--el-switch-on-color: #00ff88; --el-switch-off-color: #ff4949"
              />
            </div>
            
            <!-- 控制按钮组 -->
            <div class="control-buttons">
              <el-button type="success" size="large" :icon="VideoPlay" @click="startSpray" class="cyber-btn success">
                启动喷药
              </el-button>
              <el-button type="danger" size="large" :icon="VideoPause" @click="stopSpray" class="cyber-btn danger">
                停止喷药
              </el-button>
            </div>

            <div class="control-section">
              <div class="control-label">
                <el-icon><Monitor /></el-icon>
                <span>速度控制</span>
              </div>
              <el-slider v-model="speedValue" :min="1" :max="102" show-input />
              <el-button type="primary" :icon="Setting" @click="applySpeed" class="cyber-btn primary">
                应用速度
              </el-button>
            </div>

            <div class="control-section">
              <div class="control-label">
                <el-icon><Connection /></el-icon>
                <span>行进方向</span>
              </div>
              <div class="direction-buttons">
                <el-button type="primary" @click="setDirection(1)">前进</el-button>
                <el-button type="warning" @click="setDirection(0)">停止</el-button>
                <el-button type="primary" @click="setDirection(2)">后退</el-button>
              </div>
            </div>

            <div class="control-section">
              <div class="control-label">
                <el-icon><Setting /></el-icon>
                <span>转向控制</span>
              </div>
              <el-slider v-model="turnPosition" :min="1" :max="101" show-input />
              <el-button type="primary" :icon="Setting" @click="applyTurn" class="cyber-btn primary">
                应用转向
              </el-button>
            </div>

            <el-button type="danger" size="large" :icon="Close" @click="emergencyStop" class="cyber-btn emergency">
              紧急停止
            </el-button>

            <!-- 设备状态详情 -->
            <div class="device-status">
              <div class="status-row">
                <span class="label">水泵状态:</span>
                <el-tag :type="pumpStatusColor" effect="dark">
                  {{ pumpStatusText }}
                </el-tag>
              </div>
              
              <div class="status-row">
                <span class="label">当前车速:</span>
                <div class="speed-display">
                  <el-progress 
                    :text-inside="true" 
                    :stroke-width="20" 
                    :percentage="speedPercentage"
                    color="#00ffff"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- AI问答卡片 -->
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

      <!-- 右侧地图区域 -->
      <div class="right-panel">
        <div class="cyber-card map-panel">
          <div class="card-header">
            <div class="header-icon">
              <el-icon><MapLocation /></el-icon>
            </div>
            <h2>实时轨迹监控</h2>
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
              :angle="axiosStore.responseData.slice(-1)[0]?.angle || 0"
              :vehicle-speed="axiosStore.responseData.slice(-1)[0]?.speed || 0"
              :altitude="axiosStore.responseData.slice(-1)[0]?.altitude || 900"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
/* 主页面布局 */
.main-page {
  padding-top: 70px; /* 为固定导航栏留出空间 */
  min-height: 100vh;
  background: transparent;
}

/* 状态概览区域 */
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

.status-card {
  background: rgba(12, 20, 38, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 15px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.status-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #00ffff, #00ff88);
  opacity: 0.8;
}

.status-card:hover {
  transform: translateY(-5px);
  border-color: rgba(0, 255, 255, 0.6);
  box-shadow: 0 10px 30px rgba(0, 255, 255, 0.2);
}

.status-icon {
  font-size: 2.5rem;
  color: #00ffff;
  text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
  min-width: 50px;
}

.status-info h3 {
  color: #ffffff;
  font-size: 1.1rem;
  margin-bottom: 8px;
  font-weight: 600;
}

.status-info p {
  color: #b8c5d6;
  font-size: 1.4rem;
  margin: 0;
  font-weight: 700;
}

.status-info p.online {
  color: #00ff88;
  text-shadow: 0 0 5px rgba(0, 255, 136, 0.5);
}

.status-info p.offline {
  color: #ff3366;
  text-shadow: 0 0 5px rgba(255, 51, 102, 0.5);
}

.time-display {
  font-family: 'Courier New', monospace;
  color: #00ffff !important;
  text-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
}

/* 主要内容区域 */
.main-content {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
  padding: 0 20px 20px;
  max-width: 1400px;
  margin: 0 auto;
}

/* 科幻卡片样式 */
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

.header-glow {
  position: absolute;
  top: 0;
  right: 0;
  width: 100px;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.1));
  pointer-events: none;
}

/* 控制面板样式 */
.control-content {
  padding: 25px;
}

.main-switch {
  text-align: center;
  margin-bottom: 25px;
}

.control-buttons {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 25px;
}

.control-section {
  margin-bottom: 22px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(0, 255, 255, 0.14);
  border-radius: 10px;
}

.control-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #b8c5d6;
  font-weight: 600;
  margin-bottom: 12px;
}

.control-label .el-icon {
  color: #00ffff;
}

.direction-buttons {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.cyber-btn {
  border: none;
  padding: 15px 20px;
  font-size: 1.1rem;
  font-weight: 600;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.cyber-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.cyber-btn:hover::before {
  left: 100%;
}

.cyber-btn.success {
  background: linear-gradient(135deg, #00ff88, #00cc66);
  box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
}

.cyber-btn.danger {
  background: linear-gradient(135deg, #ff3366, #cc0033);
  box-shadow: 0 0 15px rgba(255, 51, 102, 0.3);
}

.cyber-btn.primary {
  width: 100%;
  background: linear-gradient(135deg, #00ffff, #0077ff);
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.25);
}

.cyber-btn.emergency {
  width: 100%;
  margin-bottom: 25px;
  background: linear-gradient(135deg, #ff003c, #7a001d);
  box-shadow: 0 0 20px rgba(255, 0, 60, 0.35);
}

.device-status {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  padding: 20px;
  border: 1px solid rgba(0, 255, 255, 0.1);
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
}

.status-row:last-child {
  margin-bottom: 0;
}

.label {
  color: #b8c5d6;
  font-weight: 500;
}

.speed-display {
  flex: 1;
  margin-left: 15px;
}

/* AI面板样式 */
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

/* 地图面板样式 */
.map-panel {
  height: calc(100vh - 200px);
}

.map-controls {
  margin-left: auto;
}

.map-content {
  height: calc(100% - 80px);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .left-panel {
    order: 2;
  }
  
  .right-panel {
    order: 1;
  }
}

@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .main-content {
    padding: 0 10px 20px;
  }
  
  .status-overview {
    padding: 10px;
  }
  
  .card-header {
    padding: 15px;
  }
  
  .control-content {
    padding: 20px;
  }
  
  .status-card {
    padding: 15px;
  }
  
  .cyber-btn {
    padding: 12px 16px;
    font-size: 1rem;
  }
}

/* Element Plus组件自定义样式 */
:deep(.el-progress-bar__outer) {
  background: rgba(0, 0, 0, 0.3) !important;
  border-radius: 10px !important;
}

:deep(.el-progress-bar__inner) {
  border-radius: 10px !important;
}

:deep(.el-switch.is-checked .el-switch__core) {
  background-color: #00ff88 !important;
}

:deep(.el-tag.el-tag--dark.el-tag--success) {
  background-color: rgba(0, 255, 136, 0.2) !important;
  border-color: #00ff88 !important;
  color: #00ff88 !important;
}

:deep(.el-tag.el-tag--dark.el-tag--danger) {
  background-color: rgba(255, 51, 102, 0.2) !important;
  border-color: #ff3366 !important;
  color: #ff3366 !important;
}
</style>

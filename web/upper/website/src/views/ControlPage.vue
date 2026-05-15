<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import NavBarNew from '../components/NavBarNew.vue'
import { useAxiosStore } from '../stores/axios'
import { ElMessage } from 'element-plus'
import {
  Check,
  Close,
  Operation,
  Monitor,
  VideoPlay,
  VideoPause,
  Setting,
  Connection
} from '@element-plus/icons-vue'

const axiosStore = useAxiosStore()

const statusValue = ref(false)
const speedValue = ref(51)
const turnPosition = ref(51)
let timer = null

const directionText = computed(() => {
  const directionMap = ['停止', '前进', '后退']
  return directionMap[Number(axiosStore.vehicleStatus?.direction || 0)] || '未知'
})

const pumpRunning = computed(() => {
  return Boolean(axiosStore.vehicleStatus?.spray_state)
})

const pumpStatusColor = computed(() => {
  return pumpRunning.value ? 'success' : 'danger'
})

const pumpStatusText = computed(() => {
  return pumpRunning.value ? '运行' : '停止'
})

const speedPercentage = computed(() => {
  const speed = Number(axiosStore.vehicleStatus?.speed || 0)
  return Math.min((speed / 102) * 100, 100)
})

watch(statusValue, (value) => {
  axiosStore.statusPost(value)
})

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
  const labels = ['停止', '前进', '后退']
  sendControlCommand('/direction_control', { direction }, `方向已切换为${labels[direction] || '停止'}`, '方向控制失败')
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

const refreshStatus = () => {
  axiosStore.getVehicleStatus()
}

onMounted(() => {
  refreshStatus()
  axiosStore.statusPost(false)
  timer = setInterval(refreshStatus, 2000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  timer = null
})
</script>

<template>
  <NavBarNew />

  <div class="main-page">
    <div class="control-layout">
      <div class="cyber-card control-panel">
        <div class="card-header">
          <div class="header-icon">
            <el-icon><Operation /></el-icon>
          </div>
          <div>
            <h2>设备控制台</h2>
            <p class="header-subtitle">远程喷药、调速、方向与转向控制</p>
          </div>
          <div class="header-glow"></div>
        </div>

        <div class="control-content">
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
        </div>
      </div>

      <div class="cyber-card status-panel">
        <div class="card-header">
          <div class="header-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <h2>设备实时状态</h2>
          <div class="header-glow"></div>
        </div>

        <div class="device-status">
          <div class="status-row">
            <span class="label">通信状态:</span>
            <el-tag :type="axiosStore.connectStatus ? 'success' : 'danger'" effect="dark">
              {{ axiosStore.connectStatus ? '正常连接' : '连接中断' }}
            </el-tag>
          </div>

          <div class="status-row">
            <span class="label">水泵状态:</span>
            <el-tag :type="pumpStatusColor" effect="dark">
              {{ pumpStatusText }}
            </el-tag>
          </div>

          <div class="status-row">
            <span class="label">行进方向:</span>
            <el-tag type="info" effect="dark">
              {{ directionText }}
            </el-tag>
          </div>

          <div class="status-row">
            <span class="label">转向位置:</span>
            <span class="value">{{ axiosStore.vehicleStatus?.turn_position ?? '--' }}</span>
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
  </div>
</template>

<style scoped>
.main-page {
  padding-top: 90px;
  min-height: 100vh;
  background: transparent;
}

.control-layout {
  display: grid;
  grid-template-columns: minmax(360px, 520px) minmax(300px, 1fr);
  gap: 20px;
  max-width: 1200px;
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
  margin-bottom: 0;
  background: linear-gradient(135deg, #ff003c, #7a001d);
  box-shadow: 0 0 20px rgba(255, 0, 60, 0.35);
}

.device-status {
  padding: 25px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  margin-bottom: 18px;
}

.status-row:last-child {
  margin-bottom: 0;
}

.label {
  color: #b8c5d6;
  font-weight: 500;
  white-space: nowrap;
}

.value {
  color: #00ffff;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.speed-display {
  flex: 1;
  min-width: 180px;
}

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

:deep(.el-tag.el-tag--dark.el-tag--info) {
  background-color: rgba(0, 212, 255, 0.16) !important;
  border-color: #00d4ff !important;
  color: #00d4ff !important;
}

@media (max-width: 1024px) {
  .control-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .main-page {
    padding-top: 80px;
  }

  .control-layout {
    padding: 0 10px 20px;
  }

  .card-header {
    padding: 15px;
  }

  .control-content,
  .device-status {
    padding: 20px;
  }

  .cyber-btn {
    padding: 12px 16px;
    font-size: 1rem;
  }

  .status-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .speed-display {
    width: 100%;
    min-width: 0;
  }
}
</style>

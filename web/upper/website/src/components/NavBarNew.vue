<template>
  <nav class="cyber-navbar">
    <div class="navbar-container">
      <!-- 左侧Logo和标题 -->
      <div class="navbar-brand">
        <div class="logo-container">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L13.09 8.26L22 9L13.09 9.74L12 16L10.91 9.74L2 9L10.91 8.26L12 2Z" fill="currentColor"/>
              <path d="M12 8C14.21 8 16 9.79 16 12C16 14.21 14.21 16 12 16C9.79 16 8 14.21 8 12C8 9.79 9.79 8 12 8Z" fill="currentColor"/>
            </svg>
          </div>
          <div class="brand-text">
            <h1 class="brand-title">智慧农业</h1>
            <span class="brand-subtitle">植保车监控系统</span>
          </div>
        </div>
      </div>

      <!-- 中间导航链接 -->
      <div class="navbar-menu">
        <router-link to="/monitor" class="nav-item" exact-active-class="active">
          <i class="nav-icon">🗺️</i>
          <span>实时监控</span>
        </router-link>
        <router-link to="/control" class="nav-item" exact-active-class="active">
          <i class="nav-icon">🎮</i>
          <span>设备控制</span>
        </router-link>
      </div>

      <!-- 右侧快捷操作 -->
      <div class="navbar-actions">
        <el-button 
          type="danger"
          class="emergency-btn"
          @click="emergencyAlert"
        >
          <el-icon><WarningFilled /></el-icon>
          紧急停止
        </el-button>

        <!-- 系统状态指示器 -->
        <div class="status-indicator" :class="{ online: isOnline }">
          <div class="status-dot"></div>
          <span class="status-text">{{ isOnline ? '在线' : '离线' }}</span>
        </div>
      </div>

      <!-- 移动端菜单按钮 -->
      <div class="mobile-menu-btn" @click="toggleMobileMenu">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>

    <!-- 移动端侧边菜单 -->
    <transition name="slide">
      <div v-if="mobileMenuOpen" class="mobile-menu">
        <div class="mobile-menu-content">
          <router-link to="/monitor" class="mobile-nav-item" @click="closeMobileMenu">
            🗺️ 实时监控
          </router-link>
          <router-link to="/control" class="mobile-nav-item" @click="closeMobileMenu">
            🎮 设备控制
          </router-link>
          <div class="mobile-actions">
            <el-button type="danger" size="large" @click="emergencyAlert">
              紧急停止
            </el-button>
          </div>
        </div>
      </div>
    </transition>
  </nav>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'

const mobileMenuOpen = ref(false)
const isOnline = ref(true)
let statusTimer = null

// 切换移动端菜单
const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

const closeMobileMenu = () => {
  mobileMenuOpen.value = false
}

// 紧急停止
const emergencyAlert = () => {
  axios.post('/emergency_stop', {})
    .then((response) => {
      const data = response.data || {}
      if (data.success) {
        ElMessage.warning(data.message || '紧急停止命令执行完成')
      } else {
        ElMessage.error(data.message || '紧急停止执行不完整')
      }
      refreshOnlineStatus()
    })
    .catch((error) => {
      const message = error.response?.data?.message || error.message || '紧急停止失败'
      ElMessage.error(`紧急停止失败: ${message}`)
    })
  closeMobileMenu()
}

// 监听窗口大小变化
const handleResize = () => {
  if (window.innerWidth > 768) {
    mobileMenuOpen.value = false
  }
}

const refreshOnlineStatus = () => {
  axios.get('/vehicle_status')
    .then((response) => {
      isOnline.value = Boolean(response.data?.connected)
    })
    .catch(() => {
      isOnline.value = false
    })
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  refreshOnlineStatus()
  statusTimer = setInterval(refreshOnlineStatus, 5000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  clearInterval(statusTimer)
})
</script>

<style scoped>
.cyber-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(12, 20, 38, 0.95);
  backdrop-filter: blur(20px);
  border-bottom: 2px solid rgba(0, 255, 255, 0.3);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.navbar-container {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 70px;
}

/* 品牌区域 */
.navbar-brand {
  display: flex;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  color: #00ffff;
  animation: logoGlow 2s ease-in-out infinite alternate;
}

@keyframes logoGlow {
  from { filter: drop-shadow(0 0 5px #00ffff); }
  to { filter: drop-shadow(0 0 15px #00ffff); }
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
  letter-spacing: 1px;
}

.brand-subtitle {
  font-size: 0.8rem;
  color: #00ffaa;
  margin-top: -2px;
}

/* 导航菜单 */
.navbar-menu {
  display: flex;
  gap: 30px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: #b8c5d6;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.nav-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.nav-item:hover::before {
  left: 100%;
}

.nav-item:hover {
  color: #00ffff;
  background: rgba(0, 255, 255, 0.1);
  transform: translateY(-2px);
}

.nav-item.active {
  color: #00ffff;
  background: rgba(0, 255, 255, 0.15);
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
}

.nav-icon {
  font-size: 1.2rem;
}

/* 导航动作区域 */
.navbar-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.emergency-btn {
  --el-color-danger: #ff3366;
  --el-color-danger-light-3: rgba(255, 51, 102, 0.7);
  --el-color-danger-light-5: rgba(255, 51, 102, 0.5);
  --el-color-danger-light-7: rgba(255, 51, 102, 0.3);
  --el-color-danger-light-8: rgba(255, 51, 102, 0.2);
  --el-color-danger-light-9: rgba(255, 51, 102, 0.1);
  animation: dangerPulse 2s ease-in-out infinite;
  border: none;
  color: white;
  background: #ff3366;
}

@keyframes dangerPulse {
  0%, 100% { box-shadow: 0 0 5px rgba(255, 51, 102, 0.5); }
  50% { box-shadow: 0 0 20px rgba(255, 51, 102, 0.8); }
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 20px;
  border: 1px solid rgba(255, 51, 102, 0.5);
}

.status-indicator.online {
  border-color: rgba(0, 255, 136, 0.5);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff3366;
  animation: statusBlink 1.5s ease-in-out infinite;
}

.status-indicator.online .status-dot {
  background: #00ff88;
}

@keyframes statusBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.status-text {
  font-size: 0.8rem;
  color: #ff3366;
  font-weight: 500;
}

.status-indicator.online .status-text {
  color: #00ff88;
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  display: none;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  padding: 5px;
}

.mobile-menu-btn span {
  width: 25px;
  height: 3px;
  background: #00ffff;
  border-radius: 2px;
  transition: all 0.3s ease;
}

/* 移动端菜单 */
.mobile-menu {
  position: fixed;
  top: 70px;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(12, 20, 38, 0.98);
  backdrop-filter: blur(20px);
  z-index: 999;
}

.mobile-menu-content {
  padding: 30px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mobile-nav-item {
  display: block;
  color: #b8c5d6;
  text-decoration: none;
  padding: 15px 20px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 255, 255, 0.2);
  transition: all 0.3s ease;
  text-align: center;
  font-size: 1.1rem;
  cursor: pointer;
}

.mobile-nav-item:hover {
  color: #00ffff;
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.5);
}

.mobile-actions {
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .navbar-menu,
  .navbar-actions {
    display: none;
  }
  
  .mobile-menu-btn {
    display: flex;
  }
  
  .brand-title {
    font-size: 1.2rem;
  }
  
  .brand-subtitle {
    font-size: 0.7rem;
  }
}

/* 过渡动画 */
.slide-enter-active, .slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from, .slide-leave-to {
  transform: translateX(-100%);
}
</style>

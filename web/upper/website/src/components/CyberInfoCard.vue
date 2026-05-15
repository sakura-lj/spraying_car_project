<template>
  <div class="cyber-info-card" :class="[type, { pulse: isPulse }]">
    <div class="card-corner-effects">
      <div class="corner top-left"></div>
      <div class="corner top-right"></div>
      <div class="corner bottom-left"></div>
      <div class="corner bottom-right"></div>
    </div>
    
    <div class="card-content">
      <div class="icon-section">
        <div class="icon-container">
          <component v-if="icon" :is="icon" class="card-icon" />
          <span v-else class="emoji-icon">{{ emoji }}</span>
        </div>
        <div class="status-indicator" :class="status"></div>
      </div>
      
      <div class="info-section">
        <h3 class="card-title">{{ title }}</h3>
        <div class="card-value">{{ value }}</div>
        <div class="card-subtitle" v-if="subtitle">{{ subtitle }}</div>
      </div>
      
      <div class="progress-section" v-if="showProgress">
        <el-progress 
          :percentage="progressValue" 
          :stroke-width="6"
          :color="progressColor"
          :show-text="false"
        />
      </div>
    </div>
    
    <div class="card-glow" :class="type"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  value: [String, Number],
  subtitle: String,
  icon: Object,
  emoji: String,
  type: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'success', 'warning', 'danger', 'info'].includes(value)
  },
  status: {
    type: String,
    default: 'normal',
    validator: (value) => ['normal', 'online', 'offline', 'warning'].includes(value)
  },
  isPulse: {
    type: Boolean,
    default: false
  },
  showProgress: {
    type: Boolean,
    default: false
  },
  progressValue: {
    type: Number,
    default: 0
  }
})

const progressColor = computed(() => {
  switch (props.type) {
    case 'success': return '#00ff88'
    case 'warning': return '#ffaa00'
    case 'danger': return '#ff3366'
    case 'info': return '#00d4ff'
    default: return '#00ffff'
  }
})
</script>

<style scoped>
.cyber-info-card {
  position: relative;
  background: rgba(12, 20, 38, 0.85);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.4s ease;
  overflow: hidden;
  cursor: pointer;
}

.cyber-info-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
  opacity: 0.8;
}

.cyber-info-card.primary {
  --primary-color: #00ffff;
  --secondary-color: #00d4ff;
}

.cyber-info-card.success {
  --primary-color: #00ff88;
  --secondary-color: #00cc66;
}

.cyber-info-card.warning {
  --primary-color: #ffaa00;
  --secondary-color: #ff8800;
}

.cyber-info-card.danger {
  --primary-color: #ff3366;
  --secondary-color: #cc0033;
}

.cyber-info-card.info {
  --primary-color: #00d4ff;
  --secondary-color: #0099cc;
}

.cyber-info-card:hover {
  transform: translateY(-5px) scale(1.02);
  border-color: var(--primary-color);
  box-shadow: 
    0 10px 30px rgba(0, 0, 0, 0.3),
    0 0 20px var(--primary-color);
}

.cyber-info-card.pulse {
  animation: cardPulse 2s ease-in-out infinite;
}

@keyframes cardPulse {
  0%, 100% {
    box-shadow: 0 0 5px var(--primary-color);
  }
  50% {
    box-shadow: 0 0 25px var(--primary-color);
  }
}

/* 角落科幻效果 */
.card-corner-effects {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid var(--primary-color);
  opacity: 0.6;
  transition: opacity 0.3s ease;
}

.corner.top-left {
  top: 8px;
  left: 8px;
  border-right: none;
  border-bottom: none;
}

.corner.top-right {
  top: 8px;
  right: 8px;
  border-left: none;
  border-bottom: none;
}

.corner.bottom-left {
  bottom: 8px;
  left: 8px;
  border-right: none;
  border-top: none;
}

.corner.bottom-right {
  bottom: 8px;
  right: 8px;
  border-left: none;
  border-top: none;
}

.cyber-info-card:hover .corner {
  opacity: 1;
}

/* 卡片内容 */
.card-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.icon-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.icon-container {
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--primary-color);
}

.card-icon {
  font-size: 24px;
  color: var(--primary-color);
}

.emoji-icon {
  font-size: 24px;
  filter: drop-shadow(0 0 5px var(--primary-color));
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #666;
  position: relative;
}

.status-indicator::after {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  animation: statusRipple 2s infinite;
}

.status-indicator.online {
  background: #00ff88;
}

.status-indicator.online::after {
  background: rgba(0, 255, 136, 0.6);
}

.status-indicator.offline {
  background: #ff3366;
}

.status-indicator.offline::after {
  background: rgba(255, 51, 102, 0.6);
}

.status-indicator.warning {
  background: #ffaa00;
}

.status-indicator.warning::after {
  background: rgba(255, 170, 0, 0.6);
}

@keyframes statusRipple {
  0% {
    transform: scale(0);
    opacity: 1;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

.info-section {
  flex: 1;
}

.card-title {
  color: #b8c5d6;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-value {
  color: #ffffff;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
  text-shadow: 0 0 10px var(--primary-color);
}

.card-subtitle {
  color: #7a8699;
  font-size: 12px;
  margin-top: 4px;
}

.progress-section {
  margin-top: 8px;
}

/* 发光效果 */
.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(
    circle,
    var(--primary-color) 0%,
    transparent 70%
  );
  opacity: 0.03;
  animation: glowRotate 8s linear infinite;
  pointer-events: none;
}

@keyframes glowRotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.cyber-info-card:hover .card-glow {
  opacity: 0.08;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .cyber-info-card {
    padding: 16px;
  }
  
  .icon-container {
    width: 40px;
    height: 40px;
  }
  
  .card-icon,
  .emoji-icon {
    font-size: 20px;
  }
  
  .card-value {
    font-size: 20px;
  }
}
</style>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const loading = ref(false)
let timer = null

const router = useRouter()

// 路由切换进度条
router.beforeEach((to, from, next) => {
    clearTimeout(timer)
    loading.value = true
    next()
})

router.afterEach(() => {
    const minDuration = 800
    timer = setTimeout(() => {
        loading.value = false
    }, minDuration)
})

// 背景粒子动画
onMounted(() => {
    createStars()
})

const createStars = () => {
    const container = document.querySelector('.stars-container')
    if (!container) return
    
    for (let i = 0; i < 100; i++) {
        const star = document.createElement('div')
        star.className = 'star'
        star.style.left = Math.random() * 100 + '%'
        star.style.top = Math.random() * 100 + '%'
        star.style.animationDelay = Math.random() * 2 + 's'
        container.appendChild(star)
    }
}
</script>

<template>
    <!-- 科幻背景 -->
    <div class="app-background">
        <div class="stars-container"></div>
        <div class="grid-overlay"></div>
        <div class="gradient-overlay"></div>
    </div>
    
    <!-- 路由切换进度条 -->
    <transition name="fade">
        <div v-if="loading" class="loading-bar">
            <div class="loading-progress"></div>
        </div>
    </transition>

    <!-- 主要内容区域 -->
    <div class="app-content">
        <router-view v-slot="{ Component }">
            <transition name="slide-fade" mode="out-in">
                <component :is="Component" />
            </transition>
        </router-view>
    </div>
</template>

<style scoped>
/* 应用根容器 */
.app-background {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    background: linear-gradient(135deg, #0c1426 0%, #1a2332 50%, #0e1932 100%);
    overflow: hidden;
}

/* 星空背景 */
.stars-container {
    position: absolute;
    width: 100%;
    height: 100%;
}

:deep(.star) {
    position: absolute;
    width: 2px;
    height: 2px;
    background: #ffffff;
    border-radius: 50%;
    animation: twinkle 2s infinite ease-in-out;
}

@keyframes twinkle {
    0%, 100% { opacity: 0.3; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.2); }
}

/* 网格覆盖层 */
.grid-overlay {
    position: absolute;
    width: 100%;
    height: 100%;
    background-image: 
        linear-gradient(90deg, rgba(0, 255, 255, 0.1) 1px, transparent 1px),
        linear-gradient(rgba(0, 255, 255, 0.1) 1px, transparent 1px);
    background-size: 50px 50px;
    animation: gridMove 20s linear infinite;
}

@keyframes gridMove {
    0% { transform: translate(0, 0); }
    100% { transform: translate(50px, 50px); }
}

/* 渐变覆盖层 */
.gradient-overlay {
    position: absolute;
    width: 100%;
    height: 100%;
    background: radial-gradient(
        circle at 30% 20%,
        rgba(0, 255, 255, 0.1) 0%,
        transparent 50%
    ),
    radial-gradient(
        circle at 70% 80%,
        rgba(0, 255, 136, 0.08) 0%,
        transparent 50%
    );
    animation: gradientShift 15s ease-in-out infinite;
}

@keyframes gradientShift {
    0%, 100% { opacity: 0.8; }
    50% { opacity: 1; }
}

/* 加载进度条 */
.loading-bar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: rgba(0, 255, 255, 0.2);
    z-index: 9999;
    overflow: hidden;
}

.loading-progress {
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, #00ffff, #00ff88, #00ffff);
    animation: loadingMove 1.5s ease-in-out infinite;
    box-shadow: 0 0 10px rgba(0, 255, 255, 0.8);
}

@keyframes loadingMove {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* 主内容区域 */
.app-content {
    position: relative;
    min-height: 100vh;
    backdrop-filter: blur(0.5px);
}

/* 过渡动画 */
.fade-enter-active, .fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
    opacity: 0;
}

.slide-fade-enter-active {
    transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.slide-fade-leave-active {
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.slide-fade-enter-from {
    transform: translateX(20px);
    opacity: 0;
}

.slide-fade-leave-to {
    transform: translateX(-20px);
    opacity: 0;
}

/* 滚动条美化 */
:deep(*::-webkit-scrollbar) {
    width: 8px;
    height: 8px;
}

:deep(*::-webkit-scrollbar-track) {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
}

:deep(*::-webkit-scrollbar-thumb) {
    background: linear-gradient(45deg, #00ffff, #00ff88);
    border-radius: 4px;
}

:deep(*::-webkit-scrollbar-thumb:hover) {
    background: linear-gradient(45deg, #00cccc, #00cc66);
}
</style>
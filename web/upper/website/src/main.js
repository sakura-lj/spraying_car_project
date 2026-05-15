import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './style.css'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// element-plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'


const vuetify = createVuetify({
    components,
    directives,
  })

const app = createApp(App)

app.use(createPinia())
app.use(ElementPlus)
app.use(vuetify)
app.use(router)

app.mount('#app')

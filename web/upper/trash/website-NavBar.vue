<script setup>
import { useResizeStore } from '@/stores/WindowResize';
import { useRouter } from 'vue-router'

// const resizeStore = useResizeStore()
const router = useRouter()

function pushPage(name) {
  router.push(name)
} 

</script>

<template>
  <v-card color="grey-lighten-5" elevation="3" rounded-0>
    <div class="flex felx=row flex-nowrap justify-center pb-9 pt-2 backdrop-blur-sm">
      <div class="absolute left-10 top-3 cursor-pointer font-bold" @click="pushPage('./')">
        <!-- <v-img :width="100" aspect-ratio="16/9" cover src="../../public/logo2.png">
        </v-img> -->
        云端智动”果园高压风送式喷药车
      </div>
    </div>
</v-card>
  <br/>
</template>


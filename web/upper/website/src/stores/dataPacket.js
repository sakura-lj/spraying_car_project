import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const usePacketStore = defineStore('dataPacket', () => {

    const raw_data = ref([])
    const map_data = ref([])
    const dataCount = computed(() => raw_data.value.length)

    const raw_data_get = (newData) => {
        raw_data.value = Array.isArray(newData) ? newData : []
    }

    const map_data_process = () => {
        // 确认收到数据
        // console.log(raw_data.value)
        map_data.value = raw_data.value
            .map(item => item.location)
            .filter(location => Array.isArray(location) && location.length === 2)
        // console.log(map_data.value) // 这里最开始是空的和rawdataget最开始没获取有关系，已解决
        return map_data // 调用记得.value
    }

    // const other_data = () => {
    //     // 请求数据1
    // }

    return { raw_data_get, map_data_process, dataCount } 
}) 


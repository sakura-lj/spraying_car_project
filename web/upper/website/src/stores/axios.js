import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'

export const useAxiosStore = defineStore('axios', () => {

    // 需要初始化，因为请求需要时间，而最开始为空不存在id之类的对象就会直接报错
    const responseData = ref([
    //     {
    //     "location": [81.311819,40.55745],
    //     "target_info": [
    //     {"location": [81.311819,40.55745]},
    //     ],
    //     "pump_status": {"pump1": false, "pump2": false}
    //   },
        {
            "location": [81.31234523342393, 40.55683301927755],
            "speed": 0,
            "angle": 0,
            "altitude": 900,
            "target_info": [
                {"location": [123, 123]},
            ],
            "pump_status": {"pump1": false, "pump2": false}
        },
    ])

    const connectStatus = ref(false)
    const vehicleStatus = ref({})


    const getData = () => {
        return axios.get('/updateData', {
            responseType: 'json'
        })
            .then(response => {
                connectStatus.value = true
                const payload = Array.isArray(response.data)
                    ? response.data
                    : (response.data ? [response.data] : [])
                if (payload.length > 0) {
                    responseData.value = payload
                }
                return response.data
            })
            .catch(error => {
                console.error('数据获取失败', error)
                connectStatus.value = false // 其实是无效的，因为开关开了才会刷新数据（
                return null
            })
    }

    const getVehicleStatus = () => {
        return axios.get('/vehicle_status', {
            responseType: 'json'
        })
            .then(response => {
                vehicleStatus.value = response.data || {}
                connectStatus.value = Boolean(response.data?.connected)
                return response.data
            })
            .catch(error => {
                console.error('车辆状态获取失败', error)
                connectStatus.value = false
                return null
            })
    }

    const statusPost = (code) => {
    return axios.post('/status', {
        receive_status: code
        })
        // 接收返回的ok信息
        .then(function (response) {
            console.log(response);
            return response
        })
        .catch(function (error) {
            console.log(error);
            return null
        });
}

    return { getData, getVehicleStatus, statusPost, connectStatus, responseData, vehicleStatus } 
}) 


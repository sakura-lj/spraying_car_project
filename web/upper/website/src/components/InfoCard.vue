<script setup>

import { ref } from 'vue'
import SideBar from '../components/SideBar.vue'

</script>

<template>
    <v-layout class="bg-gray-light-5">
        <SideBar />

        <v-container align="center">
            <v-row>
                <v-col>
                    <v-card min-height="200">
                        <v-card-title class="bg-primary font-bold text-start">Item 1
                        </v-card-title>
                        <v-card-subtitle class="text-start text-primary">| 病害信息</v-card-subtitle>
                        <v-container>
                            <v-row>
                                <v-col cols="4">
                                    <v-card height="90">
                                        <v-card-subtitle class="text-start">
                                            病害范围
                                        </v-card-subtitle>
                                        <div class="text-3xl flex flex-row justify-center">10<div class="text-primary">㎡</div></div>
                                        <div class="text-end pr-3"><v-btn color="primary" size="x-small">查看详情</v-btn></div>
                                    </v-card>
                                </v-col>
                                <v-col cols="4">
                                    <v-card height="90">
                                        <v-card-subtitle class="text-start">
                                            病害种类
                                        </v-card-subtitle>
                                        <div class="text-3xl flex flex-row justify-center">2<div class="text-primary"></div></div>
                                        <div class="text-end pr-3"><v-btn color="primary" size="x-small">查看详情</v-btn></div>
                                    </v-card>
                                </v-col>
                                <v-col cols="4">
                                    <v-card height="90">
                                        <v-card-subtitle class="text-start">
                                            病害等级
                                        </v-card-subtitle>
                                        <div class="text-red-500 text-3xl font-bold">C</div>
                                        <div class="text-end pr-3"><v-btn color="primary" size="x-small">查看详情</v-btn></div>
                                    </v-card>
                                </v-col>
                            </v-row>
                        </v-container>
                    </v-card>
                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    <v-card min-height="200">
                        <v-card-subtitle class="text-start text-primary">| 无人机</v-card-subtitle>
                        <v-card class="mr-5 ml-5 mt-5 mb-5" elevation="3"><v-img height="500" cover src="../../public/airplane.png"></v-img></v-card>
                        <div class="text-end pr-5 pb-4"><v-btn color="primary" size="small">查看详情</v-btn></div>
                    </v-card>
                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    <v-card min-height="200">
                        <v-card-subtitle class="text-start text-primary">| 喷施车</v-card-subtitle>
                    </v-card>
                </v-col>
            </v-row>
            <v-row>
                
            </v-row>
        </v-container>
    </v-layout>
</template>

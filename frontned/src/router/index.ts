import { createRouter, createWebHistory } from 'vue-router'
import LrcEditor from '../views/LrcEditor.vue'

const routes = [
  {
    path: '/',
    name: 'Library',
    component: () => import('../views/Library.vue')
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('../views/Search.vue')
  },
  {
    path: '/albums',
    name: 'Albums',
    component: () => import('../views/Albums.vue')
  },
  {
    path: '/albums/:id',
    name: 'AlbumDetail',
    component: () => import('../views/AlbumDetail.vue')
  },
  {
    path: '/artists',
    name: 'Artists',
    component: () => import('../views/Artists.vue')
  },
  {
    path: '/artists/:id',
    name: 'ArtistDetail',
    component: () => import('../views/ArtistDetail.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue')
  },
  {
    path: '/interfaces',
    name: 'Interfaces',
    component: () => import('../views/Interfaces.vue')
  },
  {
    path: '/lrc-editor',
    name: 'LrcEditor',
    component: LrcEditor,
    meta: { fullScreen: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
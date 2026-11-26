import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    /**
     * 必须显式绑定 IPv4 的 127.0.0.1，不能省略。
     *
     * 省略时 Vite 默认 host 是 'localhost'，而本机 localhost 解析顺序是
     * ::1 → 127.0.0.1，于是开发服务器只绑在 IPv6 回环上，
     * 浏览器打开 http://127.0.0.1:5173 会 ERR_CONNECTION_REFUSED。
     *
     * 更麻烦的是 localhost:5173 与 127.0.0.1:5173 属于**两个不同的 origin**：
     * localStorage、缓存、cookie 各自独立，切换写法会让人以为"设置丢了"。
     * 所以全项目统一使用 127.0.0.1，这里把它写死。
     */
    host: '127.0.0.1',
    port: 5173,
    /**
     * 端口被占用时直接报错，而不是静默换成 5174。
     * 静默换端口会让文档里的地址、代理和后端联调全部对不上，新手很难察觉。
     */
    strictPort: true,
    /**
     * 接口一律写相对路径 /api/...，由这里代理到后端。
     * 这样浏览器侧始终是同源请求，不会触发 CORS；
     * 也不要把后端地址写成 localhost，后端只监听 127.0.0.1。
     */
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})

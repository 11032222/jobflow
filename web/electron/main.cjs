const { app, BrowserWindow, session } = require('electron')
const path = require('path')

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5174'
const isDev = process.env.JOBFLOW_DEV === '1' || process.env.NODE_ENV !== 'production'

function createWindow() {
  const win = new BrowserWindow({
    width: 1366,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    title: 'JobFlow 智能求职辅助系统',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev) {
    // 开发模式：加载 Vite dev server
    win.loadURL(DEV_SERVER_URL)
    win.webContents.openDevTools({ mode: 'detach' })
  } else {
    // 生产模式：加载构建产物 dist/index.html
    const indexPath = path.join(__dirname, '..', 'dist', 'index.html')
    win.loadFile(indexPath)
  }
}

app.whenReady().then(() => {
  // 允许麦克风权限，供面试问答的语音录入使用
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
    const allowed = ['media', 'audioCapture', 'videoCapture'].includes(permission)
    callback(allowed)
  })
  session.defaultSession.setPermissionCheckHandler((_webContents, permission) => {
    return ['media', 'audioCapture', 'videoCapture'].includes(permission)
  })

  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

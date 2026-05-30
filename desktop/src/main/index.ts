import { app, BrowserWindow } from 'electron'
import { join } from 'path'
import { spawn, ChildProcess } from 'child_process'
import { is } from '@electron-toolkit/utils'

let win: BrowserWindow | null = null
let apiProcess: ChildProcess | null = null

function startApiServer(): void {
  const cwd = join(__dirname, '../../../..')
  apiProcess = spawn('python3', ['-m', 'uvicorn', 'screener.main:app', '--port', '8765'], {
    cwd,
    stdio: 'inherit',
  })
}

function createWindow(): void {
  win = new BrowserWindow({
    width: 1280,
    height: 800,
    title: '株スクリーナー',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      sandbox: false,
    },
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  startApiServer()
  setTimeout(createWindow, 2000)
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  apiProcess?.kill()
  if (process.platform !== 'darwin') app.quit()
})

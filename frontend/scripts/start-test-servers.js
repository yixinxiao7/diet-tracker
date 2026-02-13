import { spawn } from 'node:child_process'

const mockPort = Number(process.env.MOCK_API_PORT || 8787)
const appPort = Number(process.env.VITE_PORT || 5173)

const env = {
  ...process.env,
  MOCK_API_PORT: String(mockPort),
  VITE_API_BASE_URL: process.env.VITE_API_BASE_URL || `http://localhost:${mockPort}`,
  VITE_AUTH_BYPASS: process.env.VITE_AUTH_BYPASS || 'true',
}

const mockApi = spawn('npm', ['run', 'mock-api'], {
  stdio: 'inherit',
  env,
})

const vite = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(appPort)], {
  stdio: 'inherit',
  env,
})

function shutdown(signal) {
  if (signal) {
    mockApi.kill(signal)
    vite.kill(signal)
  } else {
    mockApi.kill()
    vite.kill()
  }
}

process.on('SIGINT', () => shutdown('SIGINT'))
process.on('SIGTERM', () => shutdown('SIGTERM'))
process.on('exit', () => shutdown())

mockApi.on('exit', (code) => {
  if (code !== 0) {
    process.exitCode = code
  }
})

vite.on('exit', (code) => {
  if (code !== 0) {
    process.exitCode = code
  }
})

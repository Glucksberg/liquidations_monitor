module.exports = {
  apps: [{
    name: "integrated_monitor",
    script: "integrated_monitor.py",
    interpreter: "venv/bin/python",
    autorestart: true,
    watch: false,
    max_memory_restart: "500M",
    log_date_format: "YYYY-MM-DD HH:mm:ss",
    env: {
      NODE_ENV: "production"
    }
  }]
}; 
# gunicorn_config.py

# import multiprocessing

workers =  1
bind = '0.0.0.0:8000'
backlog = 2048

# 🚨 worker_class를 gevent_websocket으로 변경합니다. 🚨
worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'

timeout = 120 
daemon = False
accesslog = '/var/log/gunicorn/access.log'
errorlog = '/var/log/gunicorn/error.log'
loglevel = 'info'
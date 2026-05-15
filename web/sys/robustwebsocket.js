class RobustWebSocket {
    constructor(url, options = {}) {
        this.url = url;

        this.reconnectInterval = options.reconnectInterval || 1000;
        this.maxReconnectInterval = options.maxReconnectInterval || 30000;
        this.keepAliveInterval = options.keepAliveInterval || 15000;
        this.connectionTimeout = options.connectionTimeout || 10000;

        this.ws = null;
        this.queue = [];

        this.connected = false;
        this.forcedClose = false;

        this.reconnectAttempts = 0;

        this.pingTimer = null;
        this.timeoutTimer = null;

        this.handlers = {
            open: () => {},
            message: () => {},
            close: () => {},
            error: () => {}
        };

        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.url);

        let timeout = setTimeout(() => {
            this._log("Connection timeout");
            this.ws.close();
        }, this.connectionTimeout);

        this.ws.onopen = () => {
            clearTimeout(timeout);

            this._log("Connected");
            this.connected = true;
            this.reconnectAttempts = 0;

            this.flushQueue();
            this.startKeepAlive();

            this.handlers.open();
        };

        this.ws.onmessage = (event) => {
            // If server replies with pong, reset timeout
            if (event.data === "pong") {
                this._resetTimeout();
                return;
            }

            this.handlers.message(event.data);
        };

        this.ws.onerror = (err) => {
            this._log("Error", err);
            this.handlers.error(err);
        };

        this.ws.onclose = () => {
            clearTimeout(timeout);

            this._log("Disconnected");
            this.connected = false;

            this.stopKeepAlive();
            this.handlers.close();

            if (!this.forcedClose) {
                this.reconnect();
            }
        };
    }

    reconnect() {
        let delay = Math.min(
            this.reconnectInterval * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectInterval
        );

        this._log(`Reconnecting in ${delay}ms`);

        setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
        }, delay);
    }

    send(data) {
        if (this.connected) {
            this.ws.send(data);
        } else {
            this.queue.push(data);
        }
    }

    flushQueue() {
        while (this.queue.length > 0) {
            this.ws.send(this.queue.shift());
        }
    }

    startKeepAlive() {
        this.pingTimer = setInterval(() => {
            if (this.connected) {
                this._log("Ping");
                this.ws.send("ping");
                this._startTimeout();
            }
        }, this.keepAliveInterval);
    }

    stopKeepAlive() {
        clearInterval(this.pingTimer);
        clearTimeout(this.timeoutTimer);
    }

    _startTimeout() {
        clearTimeout(this.timeoutTimer);
        this.timeoutTimer = setTimeout(() => {
            this._log("Ping timeout -> reconnect");
            this.ws.close();
        }, this.connectionTimeout);
    }

    _resetTimeout() {
        clearTimeout(this.timeoutTimer);
    }

    close() {
        this._log("Manual close");
        this.forcedClose = true;
        this.stopKeepAlive();
        if (this.ws) {
            this.ws.close();
        }
    }

    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event] = handler;
        }
    }

    _log(...args) {
        console.debug("[RobustWebSocket]", ...args);
    }
}

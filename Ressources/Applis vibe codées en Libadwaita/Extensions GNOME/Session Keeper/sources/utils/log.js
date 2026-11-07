export class Log {
    static _instance;
    static _debugEnabled = true;
    prefix;
    constructor(prefix = 'SessionKeeper') {
        this.prefix = prefix;
    }
    static getDefault() {
        if (!Log._instance) {
            Log._instance = new Log();
        }
        return Log._instance;
    }
    static setDebugEnabled(enabled) {
        Log._debugEnabled = enabled;
    }
    get debugEnabled() {
        return Log._debugEnabled;
    }
    info(message) {
        if (this.debugEnabled) {
            log(`[INFO ][${this.prefix}] ${message}`);
        }
    }
    error(error, message = '') {
        const err = error instanceof Error ? error : new Error(String(error));
        logError(err, `[ERROR][${this.prefix}] ${message}`);
    }
    warning(message) {
        if (this.debugEnabled) {
            log(`[WARN ][${this.prefix}] ${message}`);
        }
    }
}

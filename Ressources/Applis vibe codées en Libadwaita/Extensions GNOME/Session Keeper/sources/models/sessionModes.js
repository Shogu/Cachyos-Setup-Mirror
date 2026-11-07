export var SaveSessionMode;
(function (SaveSessionMode) {
    SaveSessionMode[SaveSessionMode["AUTO"] = 0] = "AUTO";
    SaveSessionMode[SaveSessionMode["MANUAL"] = 1] = "MANUAL";
})(SaveSessionMode || (SaveSessionMode = {}));
export var RestoreSessionMode;
(function (RestoreSessionMode) {
    RestoreSessionMode[RestoreSessionMode["NEVER"] = 0] = "NEVER";
    RestoreSessionMode[RestoreSessionMode["LOGIN"] = 1] = "LOGIN";
    RestoreSessionMode[RestoreSessionMode["BOOT"] = 2] = "BOOT";
    RestoreSessionMode[RestoreSessionMode["NOTIFICATION"] = 3] = "NOTIFICATION";
})(RestoreSessionMode || (RestoreSessionMode = {}));

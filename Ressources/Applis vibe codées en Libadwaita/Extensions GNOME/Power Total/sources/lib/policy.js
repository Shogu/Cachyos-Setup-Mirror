// SPDX-License-Identifier: GPL-3.0-only
// Pure decisions, also exercised by the tests without GNOME or D-Bus.
export function chooseProfile(state, config, appsActive, weakAdapter) {
    if (weakAdapter || (state.onBattery && state.lowBattery && config.lowBatterySaver))
        return 'power-saver';
    if (appsActive) return state.onBattery ? config.appsBattery : config.appsAC;
    return state.onBattery ? config.battery : config.ac;
}

export function supportedProfile(requested, available) {
    if (available.includes(requested)) return requested;
    if (available.includes('balanced')) return 'balanced';
    return available.includes('power-saver') ? 'power-saver' : null;
}

export function canRemember(state, config, appsActive, weakAdapter) {
    return config.remember && !appsActive && !weakAdapter && !(state.lowBattery && config.lowBatterySaver);
}

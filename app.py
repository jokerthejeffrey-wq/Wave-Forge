from flask import Flask, render_template_string, jsonify, request, send_file
import os
import re
import io
import shutil
import tempfile
import subprocess

app = Flask(__name__)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def build_presets():
    groups = [
        ("Pad",
         ["Soft", "Wide", "Slow", "Warm", "Deep", "Dream", "Frost", "Velvet", "Silent", "Dawn"],
         ["Pad", "Air", "Cloud", "Field", "Wash", "Layer", "Fog", "Halo", "Space", "Bloom"]),

        ("Pluck",
         ["Clean", "Tiny", "Sharp", "Glass", "Wood", "Bright", "Muted", "Short", "Crystal", "Dust"],
         ["Pluck", "Tap", "Pick", "Ping", "String", "Drop", "Spark", "Note", "Bell", "Click"]),

        ("Bass",
         ["Low", "Dark", "Round", "Heavy", "Sub", "Rubber", "Soft", "Dirty", "Deep", "Mono"],
         ["Bass", "Growl", "Body", "Weight", "Line", "Pulse", "Drop", "Hit", "Root", "Wave"]),

        ("Lead",
         ["Clean", "Thin", "Bright", "Sharp", "Wide", "Digital", "Smooth", "Fast", "Nasal", "Glass"],
         ["Lead", "Beam", "Hook", "Line", "Tone", "Edge", "Voice", "Signal", "Peak", "Trace"]),

        ("SFX",
         ["Rise", "Fall", "Cold", "Air", "Noise", "Metal", "Ghost", "Reverse", "Impact", "Broken"],
         ["FX", "Sweep", "Hit", "Lift", "Dust", "Crash", "Stab", "Riser", "Drop", "Spark"]),

        ("Instrument",
         ["Clean", "Small", "Nylon", "Organ", "Bell", "Guitar", "Flute", "String", "Piano", "Kalimba"],
         ["Tone", "Body", "Pick", "Layer", "Note", "Mock", "Air", "Pad", "Key", "Tap"]),

        ("Chill",
         ["Ocean", "Late", "Blue", "Rain", "Moon", "Calm", "Night", "Empty", "Light", "Sleep"],
         ["Sample", "Loop", "Chord", "Mist", "Memory", "Room", "Tape", "Moment", "Drift", "Air"]),

        ("Texture",
         ["Grain", "Cloud", "Static", "Dust", "Analog", "Broken", "Frozen", "Tape", "Noise", "Hollow"],
         ["Texture", "Layer", "Bed", "Field", "Matter", "Space", "Wash", "Drift", "Skin", "Surface"]),

        ("Keys",
         ["Soft", "Old", "Warm", "Tiny", "Glass", "Dry", "Muted", "Bright", "Felt", "Round"],
         ["Key", "Chord", "Piano", "Organ", "Bell", "Note", "Stack", "Tone", "Room", "Phrase"]),

        ("Perc",
         ["Click", "Snap", "Tick", "Wood", "Dust", "Metal", "Tiny", "Hard", "Dry", "Soft"],
         ["Perc", "Tap", "Knock", "Hit", "Noise", "Rim", "Pulse", "Clack", "Stick", "Shot"]),
    ]

    seqs = {
        "Pad": [48, 55, 60, 64, 67, 64, 60, 55],
        "Pluck": [60, 64, 67, 72, 67, 64, 60, 55],
        "Bass": [36, 36, 43, 36, 39, 36, 43, 39],
        "Lead": [60, 63, 67, 70, 72, 70, 67, 63],
        "SFX": [48, 50, 55, 60, 67, 72, 79, 84],
        "Instrument": [52, 59, 64, 67, 71, 67, 64, 59],
        "Chill": [48, 52, 55, 60, 64, 60, 55, 52],
        "Texture": [36, 43, 48, 55, 60, 55, 48, 43],
        "Keys": [60, 64, 67, 71, 72, 71, 67, 64],
        "Perc": [48, 48, 55, 48, 60, 48, 55, 48],
    }

    waves = {
        "Pad": ["sine", "organ", "vowel", "glass"],
        "Pluck": ["triangle", "glass", "pulse", "bright"],
        "Bass": ["sawtooth", "square", "pulse", "organ"],
        "Lead": ["square", "bright", "pulse", "vowel"],
        "SFX": ["metal", "bright", "glass", "noiseform"],
        "Instrument": ["triangle", "organ", "glass", "hollow"],
        "Chill": ["sine", "triangle", "vowel", "glass"],
        "Texture": ["glass", "metal", "vowel", "bright"],
        "Keys": ["triangle", "organ", "glass", "hollow"],
        "Perc": ["pulse", "square", "metal", "noiseform"],
    }

    presets = []
    index = 0

    for group, left_words, right_words in groups:
        for i in range(10):
            name = f"{left_words[i]} {right_words[i]}"
            wave_a = waves[group][i % len(waves[group])]
            wave_b = waves[group][(i + 1) % len(waves[group])]

            is_bass = group == "Bass"
            is_sfx = group == "SFX"
            is_perc = group == "Perc"
            is_pad = group in ["Pad", "Chill", "Texture"]

            preset = {
                "id": slugify(f"{group}-{name}-{index}"),
                "name": name,
                "type": group,

                "osc1_on": True,
                "osc1_wave": wave_a,
                "osc1_level": round(0.50 + ((index * 7) % 35) / 100, 2),
                "osc1_oct": -1 if is_bass else 0,
                "osc1_semi": [0, 0, 7, 12][index % 4],
                "osc1_detune": -8 + (index % 17),
                "osc1_pan": round(-0.25 + ((index * 3) % 50) / 100, 2),

                "osc2_on": False if is_perc else True,
                "osc2_wave": wave_b,
                "osc2_level": round(0.20 + ((index * 5) % 45) / 100, 2),
                "osc2_oct": 1 if is_pad else 0,
                "osc2_semi": [0, 7, 12, -12][index % 4],
                "osc2_detune": -6 + (index % 13),
                "osc2_pan": round(0.25 - ((index * 4) % 50) / 100, 2),

                "sub_on": True if is_bass else index % 3 == 0,
                "sub_wave": "sine" if index % 2 == 0 else "triangle",
                "sub_level": 0.35 if is_bass else round(0.05 + ((index * 2) % 20) / 100, 2),
                "sub_oct": -2 if is_bass else -1,

                "noise_on": True if is_sfx or is_perc or group == "Texture" else index % 7 == 0,
                "noise_type": ["white", "dark", "bright"][index % 3],
                "noise_level": round((0.08 if is_sfx else 0.04 if is_perc else 0.02) + ((index % 5) / 100), 2),

                "filter_type": ["lowpass", "bandpass", "highpass"][index % 3] if is_sfx else "lowpass",
                "cutoff": 650 if is_bass else 2400 + ((index * 137) % 6500),
                "q": round(1.0 + ((index * 3) % 80) / 10, 1),

                "attack": 0.01 if is_bass or is_perc else round(0.08 + ((index * 4) % 60) / 100, 3),
                "decay": 0.18 if is_perc else round(0.15 + ((index * 5) % 85) / 100, 2),
                "sustain": 0.20 if group in ["Pluck", "Perc"] else round(0.35 + ((index * 3) % 50) / 100, 2),
                "release": 0.18 if is_perc else 0.25 if is_bass else round(0.40 + ((index * 6) % 130) / 100, 2),

                "drive": 0.22 if is_bass else 0.12 if is_sfx else round(((index * 2) % 18) / 100, 2),
                "delay": 0.02 if is_bass or is_perc else round(0.06 + ((index * 3) % 28) / 100, 2),
                "feedback": round(0.10 + ((index * 2) % 25) / 100, 2),
                "reverb": 0.04 if is_bass else round(0.08 + ((index * 4) % 30) / 100, 2),

                "bpm": 150 if is_perc or is_bass else 120 + (index % 35),
                "gate": 0.45 if group in ["Pluck", "Perc"] else 0.72,
                "master": 0.08 if is_bass else 0.10 if is_perc else 0.12,

                "sequence": seqs[group],
            }

            presets.append(preset)
            index += 1

    return presets[:100]


PRESETS = build_presets()

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>WaveForge</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
:root {
    --bg: #080808;
    --panel: #0f0f0f;
    --panel2: #141414;
    --field: #090909;
    --line: #252525;
    --line2: #1a1a1a;
    --text: #eeeeee;
    --muted: #8a8a8a;
    --key-white: #dddddd;
    --key-black: #111111;
    --key-on: #777777;
}

body.light {
    --bg: #f2f2f2;
    --panel: #ffffff;
    --panel2: #f7f7f7;
    --field: #ffffff;
    --line: #d0d0d0;
    --line2: #e3e3e3;
    --text: #111111;
    --muted: #666666;
    --key-white: #ffffff;
    --key-black: #111111;
    --key-on: #bbbbbb;
}

* {
    box-sizing: border-box;
    user-select: none;
    -webkit-user-drag: none;
}

html,
body {
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
    cursor: default;
}

button,
select,
input {
    font-family: inherit;
}

input,
select {
    user-select: auto;
}

.app {
    height: 100vh;
    display: grid;
    grid-template-rows: 48px 1fr 46px;
}

.top {
    border-bottom: 1px solid var(--line);
    background: var(--panel);
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
}

.logo {
    padding-left: 14px;
    font-size: 18px;
    font-weight: 700;
}

.actions {
    display: flex;
    gap: 8px;
    padding-right: 12px;
}

button,
select,
.search {
    height: 30px;
    border: 1px solid var(--line);
    background: var(--panel2);
    color: var(--text);
    padding: 0 10px;
    border-radius: 0;
    outline: none;
}

.search {
    width: 100%;
}

button {
    cursor: pointer;
}

button:hover {
    background: var(--bg);
}

button.active {
    background: var(--text);
    color: var(--bg);
}

.main {
    min-height: 0;
    display: grid;
    grid-template-columns: 230px 1fr 360px;
}

.left,
.right {
    background: var(--panel);
    overflow: auto;
}

.left {
    border-right: 1px solid var(--line);
}

.right {
    border-left: 1px solid var(--line);
}

.block {
    border-bottom: 1px solid var(--line);
    padding: 12px;
}

.title {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 10px;
}

.preset {
    border: 1px solid var(--line);
    background: var(--panel2);
    padding: 10px;
    margin-bottom: 8px;
    cursor: pointer;
}

.preset:hover,
.preset.active {
    border-color: var(--text);
}

.preset b {
    display: block;
    font-size: 13px;
    margin-bottom: 4px;
}

.preset span {
    font-size: 12px;
    color: var(--muted);
}

.center {
    min-width: 0;
    min-height: 0;
    display: grid;
    grid-template-rows: 62px 1fr 122px;
    background: var(--bg);
}

.sound {
    border-bottom: 1px solid var(--line);
    background: var(--panel);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 14px;
}

.sound-name {
    font-size: 21px;
    font-weight: 700;
}

.sound-type {
    border: 1px solid var(--line);
    padding: 7px 10px;
    color: var(--muted);
    font-size: 12px;
}

.graph {
    position: relative;
    background: var(--field);
    border-bottom: 1px solid var(--line);
}

.graph-label {
    position: absolute;
    left: 12px;
    top: 10px;
    color: var(--muted);
    font-size: 11px;
    z-index: 2;
}

canvas {
    width: 100%;
    height: 100%;
    display: block;
}

.controls {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.ctrl label {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--muted);
    margin-bottom: 7px;
}

.ctrl b {
    color: var(--text);
    font-weight: 400;
}

.ctrl input[type="range"] {
    width: 100%;
    height: 3px;
    appearance: none;
    background: var(--line);
    outline: none;
    cursor: ew-resize;
}

.ctrl input[type="range"]::-webkit-slider-thumb {
    appearance: none;
    width: 11px;
    height: 17px;
    background: var(--text);
    border: 1px solid var(--bg);
    cursor: ew-resize;
}

.ctrl input[type="range"]::-moz-range-thumb {
    width: 11px;
    height: 17px;
    background: var(--text);
    border: 1px solid var(--bg);
    border-radius: 0;
    cursor: ew-resize;
}

.row2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 10px;
}

.row3 {
    display: grid;
    grid-template-columns: 68px 1fr 70px;
    gap: 8px;
    margin-bottom: 10px;
    align-items: center;
}

.row4 {
    display: grid;
    grid-template-columns: 68px 1fr 62px 62px;
    gap: 8px;
    margin-bottom: 10px;
    align-items: center;
}

.toggle {
    display: flex;
    gap: 7px;
    align-items: center;
    font-size: 12px;
    color: var(--muted);
}

.toggle input {
    accent-color: var(--text);
}

.small-canvas {
    height: 110px;
    border: 1px solid var(--line);
    background: var(--field);
}

.keyboard-box {
    border-top: 1px solid var(--line);
    background: var(--panel);
    padding: 10px 12px;
    overflow: hidden;
}

.keyboard-top {
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
}

.keyboard {
    height: 74px;
    display: flex;
    overflow: hidden;
}

.key {
    width: 32px;
    height: 74px;
    background: var(--key-white);
    border: 1px solid #777;
    cursor: pointer;
    touch-action: none;
}

body.light .key {
    border-color: #bdbdbd;
}

.key.black {
    width: 20px;
    height: 48px;
    background: var(--key-black);
    z-index: 2;
    margin-left: -10px;
    margin-right: -10px;
}

.key.on {
    background: var(--key-on);
}

.footer {
    border-top: 1px solid var(--line);
    background: var(--panel);
    display: grid;
    grid-template-columns: 180px 1fr 220px;
    gap: 12px;
    align-items: center;
    padding: 0 12px;
}

.transport {
    display: flex;
    gap: 8px;
}

.status {
    font-size: 12px;
    color: var(--muted);
}

.meter {
    height: 7px;
    border: 1px solid var(--line);
    background: var(--field);
}

.meter div {
    height: 100%;
    width: 1%;
    background: var(--text);
}

@media (max-width: 1000px) {
    html,
    body {
        overflow: auto;
    }

    .app {
        height: auto;
    }

    .main {
        grid-template-columns: 1fr;
    }

    .left,
    .right {
        display: none;
    }

    .center {
        min-height: 750px;
    }

    .top {
        grid-template-columns: 1fr;
        padding: 10px 0;
        gap: 8px;
    }

    .actions {
        padding-left: 14px;
        justify-content: flex-start;
    }
}
</style>
</head>

<body>
<div class="app">

<header class="top">
    <div class="logo">WaveForge</div>

    <div class="actions">
        <select id="exportFormat">
            <option value="wav">WAV</option>
            <option value="mp3">MP3</option>
        </select>
        <button id="exportBtn">Export</button>
        <button id="themeBtn">Light</button>
        <button id="topPlayBtn">Play</button>
    </div>
</header>

<main class="main">

    <aside class="left">
        <div class="block">
            <div class="title">Find</div>
            <input class="search" id="presetSearch" placeholder="Search">
            <div style="height:8px"></div>
            <select id="typeFilter" style="width:100%"></select>
        </div>

        <div class="block">
            <div class="title">Presets</div>
            <div id="presetList"></div>
        </div>
    </aside>

    <section class="center">
        <div class="sound">
            <div class="sound-name" id="soundName">Preset</div>
            <div class="sound-type" id="soundType">Type</div>
        </div>

        <div class="graph">
            <div class="graph-label">Mixed Wave</div>
            <canvas id="waveCanvas"></canvas>
        </div>

        <div class="keyboard-box">
            <div class="keyboard-top">
                <span>Keyboard</span>
                <span>Space / A W S E D F T G Y H U J K</span>
            </div>
            <div class="keyboard" id="keyboard"></div>
        </div>
    </section>

    <aside class="right">

        <div class="block">
            <div class="title">OSC A</div>

            <div class="row4">
                <label class="toggle"><input id="osc1_on" type="checkbox"> On</label>
                <select id="osc1_wave"></select>
                <select id="osc1_oct">
                    <option value="-2">-2</option>
                    <option value="-1">-1</option>
                    <option value="0">0</option>
                    <option value="1">+1</option>
                    <option value="2">+2</option>
                </select>
                <select id="osc1_semi">
                    <option value="-12">-12</option>
                    <option value="-7">-7</option>
                    <option value="0">0</option>
                    <option value="7">+7</option>
                    <option value="12">+12</option>
                </select>
            </div>

            <div class="controls">
                <div class="ctrl">
                    <label>Level <b id="osc1_levelVal"></b></label>
                    <input id="osc1_level" type="range" min="0" max="1" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Detune <b id="osc1_detuneVal"></b></label>
                    <input id="osc1_detune" type="range" min="-50" max="50" step="1">
                </div>
                <div class="ctrl">
                    <label>Pan <b id="osc1_panVal"></b></label>
                    <input id="osc1_pan" type="range" min="-1" max="1" step="0.01">
                </div>
            </div>
        </div>

        <div class="block">
            <div class="title">OSC B</div>

            <div class="row4">
                <label class="toggle"><input id="osc2_on" type="checkbox"> On</label>
                <select id="osc2_wave"></select>
                <select id="osc2_oct">
                    <option value="-2">-2</option>
                    <option value="-1">-1</option>
                    <option value="0">0</option>
                    <option value="1">+1</option>
                    <option value="2">+2</option>
                </select>
                <select id="osc2_semi">
                    <option value="-12">-12</option>
                    <option value="-7">-7</option>
                    <option value="0">0</option>
                    <option value="7">+7</option>
                    <option value="12">+12</option>
                </select>
            </div>

            <div class="controls">
                <div class="ctrl">
                    <label>Level <b id="osc2_levelVal"></b></label>
                    <input id="osc2_level" type="range" min="0" max="1" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Detune <b id="osc2_detuneVal"></b></label>
                    <input id="osc2_detune" type="range" min="-50" max="50" step="1">
                </div>
                <div class="ctrl">
                    <label>Pan <b id="osc2_panVal"></b></label>
                    <input id="osc2_pan" type="range" min="-1" max="1" step="0.01">
                </div>
            </div>
        </div>

        <div class="block">
            <div class="title">Sub / Noise</div>

            <div class="row3">
                <label class="toggle"><input id="sub_on" type="checkbox"> Sub</label>
                <select id="sub_wave">
                    <option value="sine">Sine</option>
                    <option value="triangle">Triangle</option>
                    <option value="square">Square</option>
                </select>
                <select id="sub_oct">
                    <option value="-3">-3</option>
                    <option value="-2">-2</option>
                    <option value="-1">-1</option>
                    <option value="0">0</option>
                </select>
            </div>

            <div class="row2">
                <label class="toggle"><input id="noise_on" type="checkbox"> Noise</label>
                <select id="noise_type">
                    <option value="white">White</option>
                    <option value="dark">Dark</option>
                    <option value="bright">Bright</option>
                </select>
            </div>

            <div class="controls">
                <div class="ctrl">
                    <label>Sub <b id="sub_levelVal"></b></label>
                    <input id="sub_level" type="range" min="0" max="1" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Noise <b id="noise_levelVal"></b></label>
                    <input id="noise_level" type="range" min="0" max="0.5" step="0.01">
                </div>
            </div>
        </div>

        <div class="block">
            <div class="title">Filter</div>

            <div class="row2" style="margin-bottom:10px">
                <select id="filter_type">
                    <option value="lowpass">Lowpass</option>
                    <option value="highpass">Highpass</option>
                    <option value="bandpass">Bandpass</option>
                </select>
                <button id="randomBtn">Random</button>
            </div>

            <div class="controls">
                <div class="ctrl">
                    <label>Cutoff <b id="cutoffVal"></b></label>
                    <input id="cutoff" type="range" min="80" max="12000" step="1">
                </div>
                <div class="ctrl">
                    <label>Res <b id="qVal"></b></label>
                    <input id="q" type="range" min="0.1" max="18" step="0.1">
                </div>
            </div>
        </div>

        <div class="block">
            <div class="title">Envelope</div>

            <div class="controls">
                <div class="ctrl">
                    <label>Attack <b id="attackVal"></b></label>
                    <input id="attack" type="range" min="0.001" max="1.5" step="0.001">
                </div>
                <div class="ctrl">
                    <label>Decay <b id="decayVal"></b></label>
                    <input id="decay" type="range" min="0.02" max="2" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Sustain <b id="sustainVal"></b></label>
                    <input id="sustain" type="range" min="0" max="1" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Release <b id="releaseVal"></b></label>
                    <input id="release" type="range" min="0.03" max="3" step="0.01">
                </div>
            </div>
        </div>

        <div class="block">
            <div class="title">FX / Output</div>

            <div class="controls">
                <div class="ctrl">
                    <label>Drive <b id="driveVal"></b></label>
                    <input id="drive" type="range" min="0" max="0.5" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Delay <b id="delayVal"></b></label>
                    <input id="delay" type="range" min="0" max="0.45" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Feedback <b id="feedbackVal"></b></label>
                    <input id="feedback" type="range" min="0" max="0.65" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Reverb <b id="reverbVal"></b></label>
                    <input id="reverb" type="range" min="0" max="0.45" step="0.01">
                </div>
                <div class="ctrl">
                    <label>BPM <b id="bpmVal"></b></label>
                    <input id="bpm" type="range" min="60" max="210" step="1">
                </div>
                <div class="ctrl">
                    <label>Gate <b id="gateVal"></b></label>
                    <input id="gate" type="range" min="0.1" max="0.95" step="0.01">
                </div>
                <div class="ctrl">
                    <label>Volume <b id="masterVal"></b></label>
                    <input id="master" type="range" min="0" max="0.35" step="0.001">
                </div>
            </div>
        </div>

        <div class="block">
            <div class="title">Output</div>
            <div class="small-canvas">
                <canvas id="spectrumCanvas"></canvas>
            </div>
        </div>

    </aside>

</main>

<footer class="footer">
    <div class="transport">
        <button id="playBtn">Play</button>
        <button id="stopBtn">Stop</button>
    </div>

    <div class="status" id="status">Ready</div>

    <div class="meter">
        <div id="meterFill"></div>
    </div>
</footer>

</div>

<script>
const PRESETS = {{ presets|tojson }};
const DPR = Math.min(1.25, window.devicePixelRatio || 1);
const $ = id => document.getElementById(id);

let current = {...PRESETS[0]};
let audio = null;
let analyserData = null;
let voices = new Map();
let playing = false;
let seqTimer = null;
let seqIndex = 0;
let visualRunning = false;

const waveOptions = [
    "sine",
    "sawtooth",
    "square",
    "triangle",
    "pulse",
    "organ",
    "bright",
    "vowel",
    "glass",
    "metal",
    "hollow",
    "noiseform"
];

const controlIds = [
    "osc1_on", "osc1_wave", "osc1_level", "osc1_oct", "osc1_semi", "osc1_detune", "osc1_pan",
    "osc2_on", "osc2_wave", "osc2_level", "osc2_oct", "osc2_semi", "osc2_detune", "osc2_pan",
    "sub_on", "sub_wave", "sub_level", "sub_oct",
    "noise_on", "noise_type", "noise_level",
    "filter_type", "cutoff", "q",
    "attack", "decay", "sustain", "release",
    "drive", "delay", "feedback", "reverb",
    "bpm", "gate", "master"
];

document.addEventListener("dragstart", e => e.preventDefault());
document.addEventListener("selectstart", e => {
    const tag = e.target.tagName.toLowerCase();
    if (tag !== "input" && tag !== "select" && tag !== "option") {
        e.preventDefault();
    }
});

function fillWaveSelects() {
    for (const id of ["osc1_wave", "osc2_wave"]) {
        const s = $(id);
        s.innerHTML = "";

        waveOptions.forEach(w => {
            const opt = document.createElement("option");
            opt.value = w;
            opt.textContent = w;
            s.appendChild(opt);
        });
    }
}

function midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12);
}

function valueText(id, value) {
    value = Number(value);

    if (id === "cutoff") {
        return value >= 1000 ? (value / 1000).toFixed(1) + "k" : Math.round(value) + "Hz";
    }

    if (id === "q") return value.toFixed(1);
    if (id === "bpm") return Math.round(value);
    if (id.includes("detune")) return Math.round(value) + "ct";
    if (id.includes("pan")) return value.toFixed(2);

    if (
        id.includes("level") ||
        ["drive", "delay", "feedback", "reverb", "sustain", "gate", "master"].includes(id)
    ) {
        return Math.round(value * 100) + "%";
    }

    if (["attack", "decay", "release"].includes(id)) {
        return value.toFixed(2) + "s";
    }

    return value;
}

function cfg() {
    const rawMaster = Number($("master").value);

    return {
        osc1_on: $("osc1_on").checked,
        osc1_wave: $("osc1_wave").value,
        osc1_level: Number($("osc1_level").value),
        osc1_oct: Number($("osc1_oct").value),
        osc1_semi: Number($("osc1_semi").value),
        osc1_detune: Number($("osc1_detune").value),
        osc1_pan: Number($("osc1_pan").value),

        osc2_on: $("osc2_on").checked,
        osc2_wave: $("osc2_wave").value,
        osc2_level: Number($("osc2_level").value),
        osc2_oct: Number($("osc2_oct").value),
        osc2_semi: Number($("osc2_semi").value),
        osc2_detune: Number($("osc2_detune").value),
        osc2_pan: Number($("osc2_pan").value),

        sub_on: $("sub_on").checked,
        sub_wave: $("sub_wave").value,
        sub_level: Number($("sub_level").value),
        sub_oct: Number($("sub_oct").value),

        noise_on: $("noise_on").checked,
        noise_type: $("noise_type").value,
        noise_level: Number($("noise_level").value),

        filter_type: $("filter_type").value,
        cutoff: Number($("cutoff").value),
        q: Number($("q").value),

        attack: Number($("attack").value),
        decay: Number($("decay").value),
        sustain: Number($("sustain").value),
        release: Number($("release").value),

        drive: Number($("drive").value),
        delay: Number($("delay").value),
        feedback: Number($("feedback").value),
        reverb: Number($("reverb").value),

        bpm: Number($("bpm").value),
        gate: Number($("gate").value),

        rawMaster: rawMaster,

        // Real output volume only.
        // It does not affect the wave shape display.
        master: Math.pow(rawMaster / 0.35, 2) * 0.45
    };
}

function makePresetList() {
    const q = $("presetSearch").value.toLowerCase().trim();
    const type = $("typeFilter").value;

    $("presetList").innerHTML = "";

    PRESETS
        .filter(p => {
            const text = (p.name + " " + p.type).toLowerCase();
            const typeOk = type === "All" || p.type === type;
            const searchOk = !q || text.includes(q);
            return typeOk && searchOk;
        })
        .forEach(p => {
            const el = document.createElement("div");
            el.className = "preset";
            el.dataset.id = p.id;
            el.innerHTML = `<b>${p.name}</b><span>${p.type}</span>`;
            el.onclick = () => loadPreset(p.id);
            $("presetList").appendChild(el);
        });

    document.querySelectorAll(".preset").forEach(el => {
        el.classList.toggle("active", el.dataset.id === current.id);
    });
}

function buildTypeFilter() {
    const types = ["All", ...Array.from(new Set(PRESETS.map(p => p.type)))];

    $("typeFilter").innerHTML = "";

    types.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        $("typeFilter").appendChild(opt);
    });
}

function loadPreset(id) {
    const p = PRESETS.find(x => x.id === id);
    current = {...p};

    $("soundName").textContent = current.name;
    $("soundType").textContent = current.type;

    for (const key of controlIds) {
        const el = $(key);

        if (!el || current[key] === undefined) continue;

        if (el.type === "checkbox") {
            el.checked = Boolean(current[key]);
        } else {
            el.value = current[key];
        }
    }

    updateLabels();
    makePresetList();
    applyAudio();
    drawStatic();
}

function updateLabels() {
    for (const id of controlIds) {
        const label = $(id + "Val");
        const el = $(id);

        if (label && el) {
            label.textContent = valueText(id, el.value);
        }
    }
}

function canvas(id) {
    const c = $(id);
    const r = c.getBoundingClientRect();
    const w = Math.max(1, Math.floor(r.width));
    const h = Math.max(1, Math.floor(r.height));

    if (c.width !== Math.floor(w * DPR) || c.height !== Math.floor(h * DPR)) {
        c.width = Math.floor(w * DPR);
        c.height = Math.floor(h * DPR);
    }

    const x = c.getContext("2d");
    x.setTransform(DPR, 0, 0, DPR, 0, 0);

    return {x, w, h};
}

function graphClear(x, w, h) {
    const styles = getComputedStyle(document.body);

    x.clearRect(0, 0, w, h);
    x.fillStyle = styles.getPropertyValue("--field").trim();
    x.fillRect(0, 0, w, h);

    x.strokeStyle = styles.getPropertyValue("--line2").trim();
    x.lineWidth = 1;

    for (let i = 0; i < w; i += 28) {
        x.beginPath();
        x.moveTo(i, 0);
        x.lineTo(i, h);
        x.stroke();
    }

    for (let j = 0; j < h; j += 28) {
        x.beginPath();
        x.moveTo(0, j);
        x.lineTo(w, j);
        x.stroke();
    }
}

function sampleWave(wave, phase) {
    const p = phase - Math.floor(phase);

    if (wave === "sine") return Math.sin(phase * Math.PI * 2);
    if (wave === "sawtooth") return 2 * (p - 0.5);
    if (wave === "square") return p < 0.5 ? 1 : -1;
    if (wave === "triangle") return 1 - 4 * Math.abs(Math.round(p - 0.25) - (p - 0.25));
    if (wave === "pulse") return p < 0.24 ? 1 : -1;

    if (wave === "organ") {
        return (
            Math.sin(phase * Math.PI * 2) +
            0.50 * Math.sin(phase * Math.PI * 4) +
            0.25 * Math.sin(phase * Math.PI * 6)
        ) / 1.75;
    }

    if (wave === "bright") {
        let y = 0;
        for (let n = 1; n <= 8; n++) y += Math.sin(phase * Math.PI * 2 * n) / n;
        return y / 2;
    }

    if (wave === "vowel") {
        return (
            Math.sin(phase * Math.PI * 2) +
            0.25 * Math.sin(phase * Math.PI * 4) +
            0.70 * Math.sin(phase * Math.PI * 6) +
            0.35 * Math.sin(phase * Math.PI * 10)
        ) / 2.3;
    }

    if (wave === "glass") {
        return (
            Math.sin(phase * Math.PI * 2) +
            0.60 * Math.sin(phase * Math.PI * 14) +
            0.35 * Math.sin(phase * Math.PI * 22)
        ) / 2;
    }

    if (wave === "metal") {
        return (
            0.70 * Math.sin(phase * Math.PI * 2) +
            0.90 * Math.sin(phase * Math.PI * 17) +
            0.45 * Math.sin(phase * Math.PI * 29)
        ) / 2.1;
    }

    if (wave === "hollow") {
        return (
            Math.sin(phase * Math.PI * 2) +
            0.40 * Math.sin(phase * Math.PI * 6) -
            0.25 * Math.sin(phase * Math.PI * 12)
        ) / 1.7;
    }

    if (wave === "noiseform") {
        return Math.sin((phase * 900.123 + 12.345) * 37.91) * 0.8;
    }

    return Math.sin(phase * Math.PI * 2);
}

function drawWave() {
    const {x, w, h} = canvas("waveCanvas");
    const styles = getComputedStyle(document.body);
    const c = cfg();

    graphClear(x, w, h);

    x.strokeStyle = styles.getPropertyValue("--text").trim();
    x.lineWidth = 2;
    x.beginPath();

    for (let i = 0; i < 600; i++) {
        const t = i / 599;
        let y = 0;

        if (c.osc1_on) {
            const ratio = Math.pow(2, c.osc1_oct) * Math.pow(2, c.osc1_semi / 12);
            y += sampleWave(c.osc1_wave, t * 4 * ratio) * c.osc1_level;
        }

        if (c.osc2_on) {
            const ratio = Math.pow(2, c.osc2_oct) * Math.pow(2, c.osc2_semi / 12);
            y += sampleWave(c.osc2_wave, t * 4 * ratio) * c.osc2_level;
        }

        if (c.sub_on) {
            const ratio = Math.pow(2, c.sub_oct);
            y += sampleWave(c.sub_wave, t * 4 * ratio) * c.sub_level;
        }

        if (c.noise_on) {
            y += sampleWave("noiseform", t * 3) * c.noise_level;
        }

        // Fixed visual scale. Master volume does not affect wave sharpness.
        y = Math.max(-1, Math.min(1, y * 0.55));

        const px = t * w;
        const py = h * 0.5 + y * h * 0.32;

        if (i === 0) x.moveTo(px, py);
        else x.lineTo(px, py);
    }

    x.stroke();
}

function drawEmptySpectrum() {
    const {x, w, h} = canvas("spectrumCanvas");
    const styles = getComputedStyle(document.body);

    graphClear(x, w, h);

    x.strokeStyle = styles.getPropertyValue("--muted").trim();
    x.lineWidth = 1;
    x.beginPath();
    x.moveTo(0, h - 20);
    x.lineTo(w, h - 20);
    x.stroke();
}

function drawStatic() {
    drawWave();
    drawEmptySpectrum();
}

function drawLiveSpectrum() {
    if (!audio || !analyserData) return;

    const {x, w, h} = canvas("spectrumCanvas");
    const styles = getComputedStyle(document.body);

    graphClear(x, w, h);

    audio.analyser.getByteFrequencyData(analyserData);

    let peak = 0;

    x.strokeStyle = styles.getPropertyValue("--text").trim();
    x.lineWidth = 1.5;
    x.beginPath();

    for (let i = 0; i < analyserData.length; i += 2) {
        const v = analyserData[i] / 255;
        peak = Math.max(peak, v);

        const px = i / analyserData.length * w;
        const py = h - 15 - v * (h - 30);

        if (i === 0) x.moveTo(px, py);
        else x.lineTo(px, py);
    }

    x.stroke();
    $("meterFill").style.width = Math.max(1, Math.round(peak * 100)) + "%";
}

function visualLoop() {
    if (!visualRunning) return;

    drawLiveSpectrum();

    if (voices.size > 0 || playing) {
        setTimeout(() => requestAnimationFrame(visualLoop), 75);
    } else {
        visualRunning = false;
        $("meterFill").style.width = "1%";
        drawEmptySpectrum();
    }
}

function startVisual() {
    if (!visualRunning) {
        visualRunning = true;
        requestAnimationFrame(visualLoop);
    }
}

function makeDistortionCurve(amount) {
    const n = 2048;
    const curve = new Float32Array(n);
    const k = amount * 80;

    for (let i = 0; i < n; i++) {
        const x = i * 2 / n - 1;

        if (amount <= 0.001) {
            curve[i] = x;
        } else {
            curve[i] = ((1 + k) * x) / (1 + k * Math.abs(x));
        }
    }

    return curve;
}

function makeImpulse(ctx, seconds = 1.2, decay = 2.2) {
    const len = Math.floor(ctx.sampleRate * seconds);
    const buffer = ctx.createBuffer(2, len, ctx.sampleRate);

    for (let ch = 0; ch < 2; ch++) {
        const data = buffer.getChannelData(ch);

        for (let i = 0; i < len; i++) {
            data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
        }
    }

    return buffer;
}

function makeNoiseBuffer(ctx) {
    const len = ctx.sampleRate;
    const buffer = ctx.createBuffer(1, len, ctx.sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < len; i++) {
        data[i] = Math.random() * 2 - 1;
    }

    return buffer;
}

function makePeriodic(ctx, wave) {
    const size = 32;
    const real = new Float32Array(size);
    const imag = new Float32Array(size);

    if (wave === "pulse") {
        const duty = 0.24;
        for (let n = 1; n < size; n++) {
            imag[n] = (2 * Math.sin(n * Math.PI * duty)) / (n * Math.PI);
        }
    }

    if (wave === "organ") {
        imag[1] = 1.0;
        imag[2] = 0.5;
        imag[3] = 0.25;
        imag[4] = 0.15;
    }

    if (wave === "bright") {
        for (let n = 1; n < size; n++) {
            imag[n] = 1 / n;
        }
    }

    if (wave === "vowel") {
        imag[1] = 1.0;
        imag[2] = 0.15;
        imag[3] = 0.70;
        imag[5] = 0.35;
        imag[8] = 0.20;
    }

    if (wave === "glass") {
        imag[1] = 1.0;
        imag[7] = 0.60;
        imag[11] = 0.35;
        imag[14] = 0.20;
    }

    if (wave === "metal") {
        imag[1] = 0.7;
        imag[9] = 0.9;
        imag[15] = 0.45;
        imag[21] = 0.25;
    }

    if (wave === "hollow") {
        imag[1] = 1.0;
        imag[3] = 0.4;
        imag[6] = -0.25;
    }

    if (wave === "noiseform") {
        for (let n = 1; n < size; n++) {
            imag[n] = Math.sin(n * 19.17) / Math.sqrt(n);
        }
    }

    return ctx.createPeriodicWave(real, imag, {disableNormalization: false});
}

function createOsc(ctx, wave, freq, detune) {
    const osc = ctx.createOscillator();

    if (["sine", "sawtooth", "square", "triangle"].includes(wave)) {
        osc.type = wave;
    } else {
        osc.setPeriodicWave(makePeriodic(ctx, wave));
    }

    osc.frequency.value = freq;
    osc.detune.value = detune;

    return osc;
}

function tunedFreq(base, oct, semi) {
    return base * Math.pow(2, oct) * Math.pow(2, semi / 12);
}

async function ensureAudio() {
    if (!audio) {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();

        const input = ctx.createGain();
        const filter = ctx.createBiquadFilter();
        const shaper = ctx.createWaveShaper();
        const dry = ctx.createGain();

        const delaySend = ctx.createGain();
        const delayNode = ctx.createDelay(2);
        const feedback = ctx.createGain();

        const reverbSend = ctx.createGain();
        const convolver = ctx.createConvolver();

        const master = ctx.createGain();
        const limiter = ctx.createDynamicsCompressor();
        const analyser = ctx.createAnalyser();

        analyser.fftSize = 512;

        limiter.threshold.value = -26;
        limiter.knee.value = 4;
        limiter.ratio.value = 12;
        limiter.attack.value = 0.003;
        limiter.release.value = 0.18;

        convolver.buffer = makeImpulse(ctx);

        input.connect(filter);
        filter.connect(shaper);

        shaper.connect(dry);
        dry.connect(master);

        shaper.connect(delaySend);
        delaySend.connect(delayNode);
        delayNode.connect(feedback);
        feedback.connect(delayNode);
        delayNode.connect(master);

        shaper.connect(reverbSend);
        reverbSend.connect(convolver);
        convolver.connect(master);

        master.connect(limiter);
        limiter.connect(analyser);
        analyser.connect(ctx.destination);

        audio = {
            ctx, input, filter, shaper, dry,
            delaySend, delayNode, feedback,
            reverbSend, convolver, master,
            limiter, analyser
        };

        analyserData = new Uint8Array(analyser.frequencyBinCount);
    }

    if (audio.ctx.state !== "running") {
        await audio.ctx.resume();
    }

    applyAudio();
    return audio;
}

function applyAudio() {
    if (!audio) return;

    const c = cfg();
    const now = audio.ctx.currentTime;

    audio.filter.type = c.filter_type;
    audio.filter.frequency.setTargetAtTime(c.cutoff, now, 0.01);
    audio.filter.Q.setTargetAtTime(c.q, now, 0.01);

    audio.shaper.curve = makeDistortionCurve(c.drive);
    audio.shaper.oversample = "2x";

    audio.delaySend.gain.setTargetAtTime(c.delay, now, 0.01);
    audio.delayNode.delayTime.setTargetAtTime(0.23, now, 0.01);
    audio.feedback.gain.setTargetAtTime(c.feedback, now, 0.01);

    audio.reverbSend.gain.setTargetAtTime(c.reverb, now, 0.01);
    audio.dry.gain.setTargetAtTime(0.9, now, 0.01);

    // This is the only final volume.
    audio.master.gain.setTargetAtTime(c.master, now, 0.01);
}

function connectWithPan(ctx, source, gainValue, panValue, destination) {
    const gain = ctx.createGain();
    gain.gain.value = gainValue;

    source.connect(gain);

    if (ctx.createStereoPanner) {
        const pan = ctx.createStereoPanner();
        pan.pan.value = panValue;
        gain.connect(pan);
        pan.connect(destination);
    } else {
        gain.connect(destination);
    }
}

function connectSources(ctx, c, freq, voiceGain, startTime, stopTime) {
    const sources = [];

    if (c.osc1_on) {
        const osc = createOsc(
            ctx,
            c.osc1_wave,
            tunedFreq(freq, c.osc1_oct, c.osc1_semi),
            c.osc1_detune
        );

        connectWithPan(ctx, osc, c.osc1_level * 0.24, c.osc1_pan, voiceGain);

        osc.start(startTime);
        if (stopTime !== null) osc.stop(stopTime);

        sources.push(osc);
    }

    if (c.osc2_on) {
        const osc = createOsc(
            ctx,
            c.osc2_wave,
            tunedFreq(freq, c.osc2_oct, c.osc2_semi),
            c.osc2_detune
        );

        connectWithPan(ctx, osc, c.osc2_level * 0.24, c.osc2_pan, voiceGain);

        osc.start(startTime);
        if (stopTime !== null) osc.stop(stopTime);

        sources.push(osc);
    }

    if (c.sub_on) {
        const osc = createOsc(
            ctx,
            c.sub_wave,
            tunedFreq(freq, c.sub_oct, 0),
            0
        );

        connectWithPan(ctx, osc, c.sub_level * 0.16, 0, voiceGain);

        osc.start(startTime);
        if (stopTime !== null) osc.stop(stopTime);

        sources.push(osc);
    }

    if (c.noise_on && c.noise_level > 0.001) {
        const noise = ctx.createBufferSource();
        noise.buffer = makeNoiseBuffer(ctx);
        noise.loop = true;

        const noiseFilter = ctx.createBiquadFilter();

        if (c.noise_type === "dark") {
            noiseFilter.type = "lowpass";
            noiseFilter.frequency.value = 1400;
        } else if (c.noise_type === "bright") {
            noiseFilter.type = "highpass";
            noiseFilter.frequency.value = 2600;
        } else {
            noiseFilter.type = "bandpass";
            noiseFilter.frequency.value = 4200;
            noiseFilter.Q.value = 0.4;
        }

        noise.connect(noiseFilter);
        connectWithPan(ctx, noiseFilter, c.noise_level * 0.055, 0, voiceGain);

        noise.start(startTime);
        if (stopTime !== null) noise.stop(stopTime);

        sources.push(noise);
    }

    return sources;
}

async function noteOn(id, freq) {
    await ensureAudio();

    if (voices.has(id)) return;

    const c = cfg();
    const ctx = audio.ctx;
    const now = ctx.currentTime;

    const voiceGain = ctx.createGain();

    voiceGain.gain.setValueAtTime(0.0001, now);
    voiceGain.gain.linearRampToValueAtTime(0.22, now + c.attack);
    voiceGain.gain.linearRampToValueAtTime(0.22 * c.sustain, now + c.attack + c.decay);
    voiceGain.connect(audio.input);

    const sources = connectSources(ctx, c, freq, voiceGain, now, null);

    voices.set(id, {
        gain: voiceGain,
        sources: sources
    });

    startVisual();
}

function noteOff(id) {
    if (!audio || !voices.has(id)) return;

    const v = voices.get(id);
    const c = cfg();
    const ctx = audio.ctx;
    const now = ctx.currentTime;

    voices.delete(id);

    v.gain.gain.cancelScheduledValues(now);
    v.gain.gain.setValueAtTime(Math.max(0.0001, v.gain.gain.value), now);
    v.gain.gain.exponentialRampToValueAtTime(0.0001, now + c.release);

    for (const s of v.sources) {
        try {
            s.stop(now + c.release + 0.05);
        } catch (e) {}
    }

    setTimeout(() => {
        try {
            v.gain.disconnect();
        } catch (e) {}
    }, (c.release + 0.2) * 1000);
}

async function hardStopAudio() {
    playing = false;

    if (seqTimer) {
        clearInterval(seqTimer);
        seqTimer = null;
    }

    for (const v of voices.values()) {
        for (const s of v.sources) {
            try {
                s.stop();
            } catch (e) {}
        }

        try {
            v.gain.disconnect();
        } catch (e) {}
    }

    voices.clear();

    if (audio && audio.ctx) {
        try {
            await audio.ctx.close();
        } catch (e) {}
    }

    audio = null;
    analyserData = null;
    visualRunning = false;

    $("playBtn").classList.remove("active");
    $("topPlayBtn").classList.remove("active");
    $("playBtn").textContent = "Play";
    $("topPlayBtn").textContent = "Play";
    $("status").textContent = "Stopped";
    $("meterFill").style.width = "1%";

    drawEmptySpectrum();
}

function startLoop() {
    if (playing) return;

    playing = true;

    $("playBtn").classList.add("active");
    $("topPlayBtn").classList.add("active");
    $("playBtn").textContent = "Stop";
    $("topPlayBtn").textContent = "Stop";
    $("status").textContent = "Playing";

    ensureAudio();

    seqIndex = 0;

    const step = () => {
        const c = cfg();
        const seq = current.sequence;
        const midi = seq[seqIndex % seq.length];
        const id = "seq_" + Date.now() + "_" + seqIndex;

        const stepMs = (60 / c.bpm) * 500;
        const gateMs = stepMs * c.gate;

        noteOn(id, midiToFreq(midi));
        setTimeout(() => noteOff(id), gateMs);

        seqIndex++;
    };

    step();

    const c = cfg();
    const stepMs = (60 / c.bpm) * 500;

    seqTimer = setInterval(step, stepMs);
    startVisual();
}

function togglePlay() {
    if (playing) hardStopAudio();
    else startLoop();
}

function buildKeyboard() {
    const black = new Set([1, 3, 6, 8, 10]);

    const codeMidi = {
        KeyA: 60,
        KeyW: 61,
        KeyS: 62,
        KeyE: 63,
        KeyD: 64,
        KeyF: 65,
        KeyT: 66,
        KeyG: 67,
        KeyY: 68,
        KeyH: 69,
        KeyU: 70,
        KeyJ: 71,
        KeyK: 72
    };

    const codes = Object.keys(codeMidi);
    let codeIndex = 0;

    for (let oct = 3; oct < 6; oct++) {
        for (let i = 0; i < 12; i++) {
            const midi = 12 * (oct + 1) + i;
            const key = document.createElement("div");

            key.className = "key" + (black.has(i) ? " black" : "");

            const code = codes[codeIndex] || "";
            if (code) key.dataset.code = code;

            codeIndex++;

            const id = "mouse_" + midi;

            key.onpointerdown = e => {
                e.preventDefault();
                key.setPointerCapture(e.pointerId);
                key.classList.add("on");
                noteOn(id, midiToFreq(midi));
            };

            key.onpointerup = () => {
                key.classList.remove("on");
                noteOff(id);
            };

            key.onpointercancel = () => {
                key.classList.remove("on");
                noteOff(id);
            };

            $("keyboard").appendChild(key);
        }
    }

    window.addEventListener("keydown", e => {
        if (e.repeat) return;

        if (e.code === "Space") {
            const tag = document.activeElement.tagName.toLowerCase();

            if (tag !== "input" && tag !== "select") {
                e.preventDefault();
                togglePlay();
            }

            return;
        }

        if (codeMidi[e.code]) {
            noteOn(e.code, midiToFreq(codeMidi[e.code]));

            const key = document.querySelector(`[data-code="${e.code}"]`);
            if (key) key.classList.add("on");
        }
    });

    window.addEventListener("keyup", e => {
        if (codeMidi[e.code]) {
            noteOff(e.code);

            const key = document.querySelector(`[data-code="${e.code}"]`);
            if (key) key.classList.remove("on");
        }
    });
}

function createOfflineGraph(ctx, c) {
    const input = ctx.createGain();
    const filter = ctx.createBiquadFilter();
    const shaper = ctx.createWaveShaper();
    const dry = ctx.createGain();

    const delaySend = ctx.createGain();
    const delayNode = ctx.createDelay(2);
    const feedback = ctx.createGain();

    const reverbSend = ctx.createGain();
    const convolver = ctx.createConvolver();

    const master = ctx.createGain();
    const limiter = ctx.createDynamicsCompressor();

    filter.type = c.filter_type;
    filter.frequency.value = c.cutoff;
    filter.Q.value = c.q;

    shaper.curve = makeDistortionCurve(c.drive);
    shaper.oversample = "2x";

    delaySend.gain.value = c.delay;
    delayNode.delayTime.value = 0.23;
    feedback.gain.value = c.feedback;

    reverbSend.gain.value = c.reverb;
    convolver.buffer = makeImpulse(ctx);

    dry.gain.value = 0.9;
    master.gain.value = c.master;

    limiter.threshold.value = -26;
    limiter.knee.value = 4;
    limiter.ratio.value = 12;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.18;

    input.connect(filter);
    filter.connect(shaper);

    shaper.connect(dry);
    dry.connect(master);

    shaper.connect(delaySend);
    delaySend.connect(delayNode);
    delayNode.connect(feedback);
    feedback.connect(delayNode);
    delayNode.connect(master);

    shaper.connect(reverbSend);
    reverbSend.connect(convolver);
    convolver.connect(master);

    master.connect(limiter);
    limiter.connect(ctx.destination);

    return input;
}

function writeWav(buffer) {
    const channels = buffer.numberOfChannels;
    const rate = buffer.sampleRate;
    const length = buffer.length;
    const bytes = 44 + length * channels * 2;
    const ab = new ArrayBuffer(bytes);
    const view = new DataView(ab);

    let pos = 0;

    function str(s) {
        for (let i = 0; i < s.length; i++) view.setUint8(pos++, s.charCodeAt(i));
    }

    function u32(v) {
        view.setUint32(pos, v, true);
        pos += 4;
    }

    function u16(v) {
        view.setUint16(pos, v, true);
        pos += 2;
    }

    str("RIFF");
    u32(bytes - 8);
    str("WAVE");

    str("fmt ");
    u32(16);
    u16(1);
    u16(channels);
    u32(rate);
    u32(rate * channels * 2);
    u16(channels * 2);
    u16(16);

    str("data");
    u32(length * channels * 2);

    const data = [];

    for (let ch = 0; ch < channels; ch++) {
        data.push(buffer.getChannelData(ch));
    }

    for (let i = 0; i < length; i++) {
        for (let ch = 0; ch < channels; ch++) {
            let sample = data[ch][i];
            sample = Math.max(-1, Math.min(1, sample));
            view.setInt16(pos, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
            pos += 2;
        }
    }

    return new Blob([ab], {type: "audio/wav"});
}

async function renderExport() {
    $("status").textContent = "Rendering single note";

    const c = cfg();
    const rate = 44100;

    const shortSound = isShortSound();

    // One note only.
    // Bass exports low C.
    // Pads / chill / texture export lower C.
    // Everything else exports middle C.
    const midi = exportMidiForType();
    const freq = midiToFreq(midi);

    const noteStart = 0.05;

    // Pads become long single notes.
    // Plucks / perc become short single hits.
    const noteLength = shortSound ? 0.18 : 4.0;

    const duration = shortSound
        ? Math.max(1.0, c.attack + c.decay + c.release + 0.6)
        : noteLength + c.release + 1.0;

    const off = new OfflineAudioContext(
        2,
        Math.ceil(rate * duration),
        rate
    );

    const input = createOfflineGraph(off, c);

    const voiceGain = off.createGain();

    voiceGain.gain.setValueAtTime(0.0001, noteStart);
    voiceGain.gain.linearRampToValueAtTime(0.22, noteStart + c.attack);

    if (shortSound) {
        // Pluck / perc: short sound, no held sustain.
        voiceGain.gain.exponentialRampToValueAtTime(
            0.0001,
            noteStart + c.attack + c.decay + c.release
        );
    } else {
        // Pad / bass / lead / instrument: one long sustained note.
        voiceGain.gain.linearRampToValueAtTime(
            0.22 * c.sustain,
            noteStart + c.attack + c.decay
        );

        voiceGain.gain.setValueAtTime(
            0.22 * c.sustain,
            noteStart + noteLength
        );

        voiceGain.gain.exponentialRampToValueAtTime(
            0.0001,
            noteStart + noteLength + c.release
        );
    }

    voiceGain.connect(input);

    // ONE call only. This is the whole sample.
    connectSources(
        off,
        c,
        freq,
        voiceGain,
        noteStart,
        shortSound
            ? noteStart + c.attack + c.decay + c.release + 0.2
            : noteStart + noteLength + c.release + 0.2
    );

    const rendered = await off.startRendering();
    const wavBlob = writeWav(rendered);

    const format = $("exportFormat").value;
    const baseName = current.name
        .replace(/[^a-z0-9]+/gi, "_")
        .toLowerCase();

    if (format === "wav") {
        downloadBlob(wavBlob, baseName + "_single_note.wav");
        $("status").textContent = "Exported single note";
        return;
    }

    const form = new FormData();
    form.append("file", wavBlob, "input.wav");

    const res = await fetch("/convert-mp3", {
        method: "POST",
        body: form
    });

    if (!res.ok) {
        const text = await res.text();
        $("status").textContent = "MP3 failed";
        alert("Install ffmpeg for MP3 export.\n\n" + text);
        return;
    }

    const mp3Blob = await res.blob();

    downloadBlob(mp3Blob, baseName + "_single_note.mp3");
    $("status").textContent = "Exported single note";
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = filename;
    a.click();

    setTimeout(() => URL.revokeObjectURL(url), 3000);
}

function randomize() {
    $("osc1_on").checked = true;
    $("osc2_on").checked = Math.random() > 0.25;
    $("sub_on").checked = Math.random() > 0.5;
    $("noise_on").checked = Math.random() > 0.7;

    $("osc1_wave").value = waveOptions[Math.floor(Math.random() * waveOptions.length)];
    $("osc2_wave").value = waveOptions[Math.floor(Math.random() * waveOptions.length)];

    $("osc1_level").value = (0.35 + Math.random() * 0.55).toFixed(2);
    $("osc2_level").value = (0.15 + Math.random() * 0.60).toFixed(2);
    $("sub_level").value = (Math.random() * 0.35).toFixed(2);
    $("noise_level").value = (Math.random() * 0.15).toFixed(2);

    $("osc1_oct").value = [-1, 0, 1][Math.floor(Math.random() * 3)];
    $("osc2_oct").value = [0, 1][Math.floor(Math.random() * 2)];

    $("osc1_semi").value = [0, 7, 12][Math.floor(Math.random() * 3)];
    $("osc2_semi").value = [0, 7, 12][Math.floor(Math.random() * 3)];

    $("osc1_detune").value = Math.floor(-12 + Math.random() * 24);
    $("osc2_detune").value = Math.floor(-12 + Math.random() * 24);

    $("osc1_pan").value = (-0.4 + Math.random() * 0.8).toFixed(2);
    $("osc2_pan").value = (-0.4 + Math.random() * 0.8).toFixed(2);

    $("cutoff").value = Math.floor(350 + Math.random() * 7500);
    $("q").value = (0.5 + Math.random() * 8).toFixed(1);
    $("drive").value = (Math.random() * 0.22).toFixed(2);
    $("delay").value = (Math.random() * 0.28).toFixed(2);
    $("feedback").value = (Math.random() * 0.35).toFixed(2);
    $("reverb").value = (Math.random() * 0.30).toFixed(2);
    $("attack").value = (0.005 + Math.random() * 0.55).toFixed(3);
    $("decay").value = (0.05 + Math.random() * 0.8).toFixed(2);
    $("sustain").value = (0.15 + Math.random() * 0.75).toFixed(2);
    $("release").value = (0.12 + Math.random() * 1.2).toFixed(2);
    $("bpm").value = Math.floor(90 + Math.random() * 80);
    $("gate").value = (0.3 + Math.random() * 0.55).toFixed(2);

    updateLabels();
    applyAudio();
    drawStatic();
}

function setTheme(mode) {
    if (mode === "light") {
        document.body.classList.add("light");
        $("themeBtn").textContent = "Dark";
    } else {
        document.body.classList.remove("light");
        $("themeBtn").textContent = "Light";
    }

    localStorage.setItem("waveforge_theme", mode);
    drawStatic();
}

for (const id of controlIds) {
    const el = $(id);

    if (!el) continue;

    el.addEventListener("input", () => {
        updateLabels();
        applyAudio();
        drawStatic();
    });

    el.addEventListener("change", () => {
        updateLabels();
        applyAudio();
        drawStatic();
    });
}

$("presetSearch").addEventListener("input", makePresetList);
$("typeFilter").addEventListener("change", makePresetList);

$("playBtn").onclick = togglePlay;
$("topPlayBtn").onclick = togglePlay;
$("stopBtn").onclick = hardStopAudio;
$("randomBtn").onclick = randomize;

$("exportBtn").onclick = () => {
    renderExport().catch(err => {
        $("status").textContent = "Export failed";
        alert(err.message);
    });
};

$("themeBtn").onclick = () => {
    const isLight = document.body.classList.contains("light");
    setTheme(isLight ? "dark" : "light");
};

window.addEventListener("resize", drawStatic);

fillWaveSelects();
buildTypeFilter();
makePresetList();
buildKeyboard();

setTheme(localStorage.getItem("waveforge_theme") || "dark");
loadPreset(PRESETS[0].id);
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, presets=PRESETS)

@app.route("/api/presets")
def api_presets():
    return jsonify(PRESETS)

@app.post("/convert-mp3")
def convert_mp3():
    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        return jsonify({"error": "ffmpeg not found"}), 500

    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    temp_dir = tempfile.mkdtemp()
    wav_path = os.path.join(temp_dir, "input.wav")
    mp3_path = os.path.join(temp_dir, "output.mp3")

    try:
        request.files["file"].save(wav_path)

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i", wav_path,
                "-codec:a", "libmp3lame",
                "-b:a", "192k",
                mp3_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        with open(mp3_path, "rb") as f:
            data = io.BytesIO(f.read())

        data.seek(0)

        return send_file(
            data,
            as_attachment=True,
            download_name="waveforge_export.mp3",
            mimetype="audio/mpeg"
        )

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "ffmpeg failed",
            "details": e.stderr.decode(errors="ignore")
        }), 500

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    app.run(debug=True, port=8000)

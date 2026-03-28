/**
 * Redline Reveal — Frontend
 * Voice UI + Google Maps choropleth for NYC mortgage bias data
 */

"use strict";

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  ws: null,
  mediaRecorder: null,
  audioContext: null,
  analyser: null,
  audioStream: null,
  isListening: false,
  isConnected: false,
  mapPolygons: {},        // borough → google.maps.Polygon
  currentMapData: null,
  currentFilter: null,
  map: null,
  animFrameId: null,
};

// Borough center coordinates for labeling
const BOROUGH_CENTERS = {
  Manhattan:    { lat: 40.7831, lng: -73.9712 },
  Brooklyn:     { lat: 40.6501, lng: -73.9496 },
  Queens:       { lat: 40.7282, lng: -73.7949 },
  Bronx:        { lat: 40.8448, lng: -73.8648 },
  "Staten Island": { lat: 40.5795, lng: -74.1502 },
};

// Borough approximate polygon paths (GeoJSON-style, simplified)
const BOROUGH_PATHS = {
  Manhattan: [
    {lat:40.879,lng:-73.909},{lat:40.875,lng:-73.910},{lat:40.870,lng:-73.912},
    {lat:40.856,lng:-73.930},{lat:40.845,lng:-73.940},{lat:40.830,lng:-73.941},
    {lat:40.820,lng:-73.945},{lat:40.810,lng:-73.950},{lat:40.800,lng:-73.955},
    {lat:40.796,lng:-73.970},{lat:40.793,lng:-73.975},{lat:40.784,lng:-73.979},
    {lat:40.770,lng:-73.978},{lat:40.757,lng:-73.976},{lat:40.745,lng:-73.975},
    {lat:40.730,lng:-73.977},{lat:40.720,lng:-73.979},{lat:40.710,lng:-73.982},
    {lat:40.703,lng:-74.000},{lat:40.700,lng:-74.010},{lat:40.700,lng:-74.020},
    {lat:40.703,lng:-74.025},{lat:40.708,lng:-74.022},{lat:40.718,lng:-74.012},
    {lat:40.726,lng:-74.005},{lat:40.738,lng:-74.002},{lat:40.750,lng:-73.998},
    {lat:40.765,lng:-73.992},{lat:40.776,lng:-73.988},{lat:40.790,lng:-73.982},
    {lat:40.804,lng:-73.968},{lat:40.816,lng:-73.958},{lat:40.828,lng:-73.949},
    {lat:40.840,lng:-73.945},{lat:40.855,lng:-73.937},{lat:40.866,lng:-73.928},
    {lat:40.872,lng:-73.915},{lat:40.879,lng:-73.909},
  ],
  Brooklyn: [
    {lat:40.740,lng:-73.952},{lat:40.730,lng:-73.962},{lat:40.720,lng:-73.968},
    {lat:40.712,lng:-73.973},{lat:40.700,lng:-73.980},{lat:40.688,lng:-73.985},
    {lat:40.677,lng:-73.996},{lat:40.668,lng:-74.005},{lat:40.660,lng:-74.018},
    {lat:40.656,lng:-74.030},{lat:40.652,lng:-74.040},{lat:40.650,lng:-74.055},
    {lat:40.648,lng:-74.060},{lat:40.640,lng:-74.010},{lat:40.636,lng:-73.990},
    {lat:40.635,lng:-73.970},{lat:40.638,lng:-73.950},{lat:40.640,lng:-73.940},
    {lat:40.645,lng:-73.930},{lat:40.650,lng:-73.920},{lat:40.658,lng:-73.910},
    {lat:40.666,lng:-73.900},{lat:40.675,lng:-73.893},{lat:40.685,lng:-73.888},
    {lat:40.696,lng:-73.885},{lat:40.706,lng:-73.886},{lat:40.716,lng:-73.889},
    {lat:40.726,lng:-73.895},{lat:40.734,lng:-73.912},{lat:40.739,lng:-73.928},
    {lat:40.741,lng:-73.940},{lat:40.740,lng:-73.952},
  ],
  Queens: [
    {lat:40.800,lng:-73.700},{lat:40.790,lng:-73.710},{lat:40.780,lng:-73.720},
    {lat:40.770,lng:-73.740},{lat:40.760,lng:-73.760},{lat:40.750,lng:-73.780},
    {lat:40.745,lng:-73.800},{lat:40.740,lng:-73.820},{lat:40.738,lng:-73.840},
    {lat:40.735,lng:-73.860},{lat:40.730,lng:-73.870},{lat:40.726,lng:-73.895},
    {lat:40.716,lng:-73.889},{lat:40.706,lng:-73.886},{lat:40.696,lng:-73.885},
    {lat:40.685,lng:-73.888},{lat:40.675,lng:-73.893},{lat:40.666,lng:-73.900},
    {lat:40.658,lng:-73.910},{lat:40.650,lng:-73.920},{lat:40.645,lng:-73.930},
    {lat:40.640,lng:-73.940},{lat:40.638,lng:-73.950},{lat:40.635,lng:-73.970},
    {lat:40.636,lng:-73.990},{lat:40.640,lng:-74.010},{lat:40.648,lng:-74.060},
    {lat:40.648,lng:-73.730},{lat:40.660,lng:-73.710},{lat:40.680,lng:-73.700},
    {lat:40.720,lng:-73.695},{lat:40.760,lng:-73.690},{lat:40.800,lng:-73.700},
  ],
  Bronx: [
    {lat:40.916,lng:-73.897},{lat:40.910,lng:-73.870},{lat:40.903,lng:-73.855},
    {lat:40.896,lng:-73.840},{lat:40.887,lng:-73.832},{lat:40.878,lng:-73.836},
    {lat:40.870,lng:-73.845},{lat:40.862,lng:-73.850},{lat:40.855,lng:-73.840},
    {lat:40.848,lng:-73.830},{lat:40.842,lng:-73.840},{lat:40.840,lng:-73.855},
    {lat:40.838,lng:-73.870},{lat:40.836,lng:-73.880},{lat:40.835,lng:-73.895},
    {lat:40.838,lng:-73.910},{lat:40.843,lng:-73.920},{lat:40.850,lng:-73.930},
    {lat:40.857,lng:-73.938},{lat:40.865,lng:-73.945},{lat:40.872,lng:-73.945},
    {lat:40.879,lng:-73.930},{lat:40.885,lng:-73.918},{lat:40.891,lng:-73.910},
    {lat:40.900,lng:-73.908},{lat:40.910,lng:-73.905},{lat:40.916,lng:-73.897},
  ],
  "Staten Island": [
    {lat:40.651,lng:-74.055},{lat:40.648,lng:-74.060},{lat:40.640,lng:-74.070},
    {lat:40.630,lng:-74.080},{lat:40.620,lng:-74.090},{lat:40.610,lng:-74.100},
    {lat:40.600,lng:-74.115},{lat:40.590,lng:-74.130},{lat:40.580,lng:-74.145},
    {lat:40.570,lng:-74.155},{lat:40.562,lng:-74.165},{lat:40.558,lng:-74.175},
    {lat:40.556,lng:-74.185},{lat:40.555,lng:-74.200},{lat:40.558,lng:-74.215},
    {lat:40.562,lng:-74.225},{lat:40.570,lng:-74.235},{lat:40.578,lng:-74.240},
    {lat:40.586,lng:-74.237},{lat:40.596,lng:-74.228},{lat:40.606,lng:-74.218},
    {lat:40.616,lng:-74.200},{lat:40.625,lng:-74.178},{lat:40.632,lng:-74.160},
    {lat:40.638,lng:-74.145},{lat:40.643,lng:-74.130},{lat:40.647,lng:-74.110},
    {lat:40.650,lng:-74.090},{lat:40.652,lng:-74.075},{lat:40.651,lng:-74.055},
  ],
};

// ─── Color Scale ──────────────────────────────────────────────────────────────
function rateToColor(rate) {
  if (rate === null || rate === undefined) return "#2d3748";
  // 0% → green, 25% → yellow, 50%+ → red
  const t = Math.min(rate / 50, 1);
  if (t < 0.5) {
    // green → yellow
    const s = t * 2;
    const r = Math.round(45 + s * (255 - 45));
    const g = Math.round(106 + s * (209 - 106));
    const b = Math.round(79 + s * (102 - 79));
    return `rgb(${r},${g},${b})`;
  } else {
    // yellow → red
    const s = (t - 0.5) * 2;
    const r = Math.round(255 + s * (230 - 255));
    const g = Math.round(209 + s * (57 - 209));
    const b = Math.round(102 + s * (70 - 102));
    return `rgb(${r},${g},${b})`;
  }
}

// ─── Google Maps Init ─────────────────────────────────────────────────────────
window.initMap = function () {
  state.map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 40.7128, lng: -74.006 },
    zoom: 11,
    styles: darkMapStyles(),
    disableDefaultUI: true,
    zoomControl: true,
    mapTypeControl: false,
  });

  // Draw borough polygons
  for (const [borough, path] of Object.entries(BOROUGH_PATHS)) {
    const polygon = new google.maps.Polygon({
      paths: path,
      strokeColor: "#30363d",
      strokeOpacity: 0.9,
      strokeWeight: 1.5,
      fillColor: "#2d3748",
      fillOpacity: 0.75,
      map: state.map,
    });

    polygon.set("borough", borough);

    polygon.addListener("mouseover", (e) => showTooltip(borough, e));
    polygon.addListener("mousemove", (e) => moveTooltip(e));
    polygon.addListener("mouseout", hideTooltip);
    polygon.addListener("click", () => onBoroughClick(borough));

    state.mapPolygons[borough] = polygon;
  }

  // Borough labels rendered as map overlays (avoids deprecated Marker API)
  for (const [borough, center] of Object.entries(BOROUGH_CENTERS)) {
    const infoWindow = new google.maps.InfoWindow({
      content: `<div style="background:transparent;border:none;box-shadow:none;color:#8b949e;font-size:10px;font-weight:600;font-family:Inter,sans-serif;pointer-events:none;">${borough.toUpperCase()}</div>`,
      position: center,
      disableAutoPan: true,
    });
    infoWindow.open(state.map);
  }

  // Load initial map data
  loadMapData(null);

  // Hide loading overlay
  setTimeout(() => {
    document.getElementById("loading-overlay").classList.add("hidden");
  }, 800);
};

// ─── Choropleth Update ────────────────────────────────────────────────────────
function updateChoropleth(data) {
  state.currentMapData = data;
  const boroughData = data.borough_data || {};
  const filter = data.demographic_filter || "All applicants";

  // Update polygons with colors
  for (const [borough, polygon] of Object.entries(state.mapPolygons)) {
    const stats = boroughData[borough] || {};
    const rate = stats.denial_rate_pct;
    const color = rateToColor(rate);

    polygon.setOptions({
      fillColor: color,
      fillOpacity: rate !== null ? 0.80 : 0.35,
    });
    polygon.set("stats", stats);
  }

  // Update overlay
  document.getElementById("map-filter-display").textContent =
    filter ? `${filter} applicants` : "All applicants";

  state.currentFilter = filter;
}

function loadMapData(race) {
  const url = `${window.BACKEND_URL}/map-data${race ? `?race=${encodeURIComponent(race)}` : ""}`;
  fetch(url)
    .then(r => r.json())
    .then(data => {
      updateChoropleth(data);
      hideLoading();
    })
    .catch(err => console.error("Map data fetch error:", err));
}

function hideLoading() {
  document.getElementById("loading-overlay").classList.add("hidden");
}

// ─── Borough Tooltip ──────────────────────────────────────────────────────────
function showTooltip(borough, event) {
  const tooltip = document.getElementById("borough-tooltip");
  const stats = state.mapPolygons[borough]?.get("stats") || {};
  const rate = stats.denial_rate_pct;

  document.getElementById("tt-borough").textContent = borough;
  document.getElementById("tt-rate").textContent = rate !== null ? `${rate}%` : "No data";
  document.getElementById("tt-detail").textContent =
    stats.total ? `${stats.denied?.toLocaleString()} denied / ${stats.total?.toLocaleString()} total` : "";

  tooltip.style.display = "block";
  moveTooltip(event);
}

function moveTooltip(event) {
  const tooltip = document.getElementById("borough-tooltip");
  const container = document.getElementById("map-container");
  const rect = container.getBoundingClientRect();

  const domEvent = event.domEvent || event;
  let x = domEvent.clientX - rect.left + 12;
  let y = domEvent.clientY - rect.top + 12;

  if (x + 180 > rect.width) x -= 192;
  if (y + 120 > rect.height) y -= 132;

  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
}

function hideTooltip() {
  document.getElementById("borough-tooltip").style.display = "none";
}

function onBoroughClick(borough) {
  // Zoom to clicked borough
  const center = BOROUGH_CENTERS[borough];
  if (center) {
    state.map.panTo(center);
    state.map.setZoom(12);
  }
  // Fetch race breakdown for this borough
  fetch(`${window.BACKEND_URL}/borough/${encodeURIComponent(borough)}?breakdown=true`)
    .then(r => r.json())
    .then(data => {
      updateStatsFromBreakdown(data, borough);
    })
    .catch(console.error);
}

// ─── Stats Panel Update ───────────────────────────────────────────────────────
function updateStats(group, rate, whiteRate, total) {
  document.getElementById("stat-group").textContent = group || "—";
  document.getElementById("stat-rate").textContent = rate !== null ? `${rate}%` : "—";
  document.getElementById("stat-white").textContent = whiteRate !== null ? `${whiteRate}%` : "—";

  if (rate !== null && whiteRate !== null && whiteRate > 0) {
    const ratio = (rate / whiteRate).toFixed(1);
    document.getElementById("stat-disparity").textContent = `${ratio}×`;
  } else {
    document.getElementById("stat-disparity").textContent = "—";
  }

  document.getElementById("stat-apps").textContent = total ? total.toLocaleString() : "—";
}

function updateStatsFromBreakdown(data, borough) {
  const breakdown = data.race_breakdown || {};
  const white = breakdown["White"] || {};
  const black = breakdown["Black"] || {};
  const hispanic = breakdown["Hispanic/Latino"] || {};
  // Show most impacted group
  const mostImpacted = Object.entries(breakdown)
    .filter(([k, v]) => v.denial_rate_pct !== null && k !== "White" && k !== "Joint")
    .sort((a, b) => (b[1].denial_rate_pct || 0) - (a[1].denial_rate_pct || 0))[0];

  if (mostImpacted) {
    updateStats(
      `${mostImpacted[0]} (${borough})`,
      mostImpacted[1].denial_rate_pct,
      white.denial_rate_pct,
      mostImpacted[1].total
    );
  }
}

function updateStatsFromMapUpdate(data, filterGroup) {
  const boroughData = data.borough_data || {};
  // Sum across all boroughs
  let totalDenied = 0, totalAll = 0;
  for (const stats of Object.values(boroughData)) {
    totalDenied += stats.denied || 0;
    totalAll += stats.total || 0;
  }
  const rate = totalAll > 0 ? Math.round(totalDenied / totalAll * 100 * 10) / 10 : null;
  updateStats(filterGroup || "All", rate, null, totalAll);
}

// ─── Transcript UI ────────────────────────────────────────────────────────────
function addTranscript(role, text) {
  const section = document.getElementById("transcript-section");
  const msg = document.createElement("div");
  msg.className = `transcript-msg ${role}`;
  msg.innerHTML = `<span class="label">${role === "user" ? "You" : "Redline Reveal"}</span><span>${escapeHtml(text)}</span>`;
  section.appendChild(msg);
  section.scrollTop = section.scrollHeight;
}

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ─── Status Indicator ─────────────────────────────────────────────────────────
function setStatus(state_name, label) {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  dot.className = `status-indicator ${state_name}`;
  text.textContent = label;
}

// ─── Visualizer ───────────────────────────────────────────────────────────────
function setupVisualizer() {
  const container = document.getElementById("visualizer");
  container.innerHTML = "";
  const NUM_BARS = 24;
  for (let i = 0; i < NUM_BARS; i++) {
    const bar = document.createElement("div");
    bar.className = "bar";
    container.appendChild(bar);
  }
}

function animateVisualizer(active) {
  const bars = document.querySelectorAll(".bar");
  if (!active || !state.analyser) {
    bars.forEach(b => { b.style.height = "4px"; b.classList.remove("active"); });
    if (state.animFrameId) cancelAnimationFrame(state.animFrameId);
    return;
  }

  const dataArray = new Uint8Array(state.analyser.frequencyBinCount);

  function draw() {
    state.animFrameId = requestAnimationFrame(draw);
    state.analyser.getByteFrequencyData(dataArray);
    const step = Math.floor(dataArray.length / bars.length);
    bars.forEach((bar, i) => {
      const val = dataArray[i * step] / 255;
      const height = 4 + val * 36;
      bar.style.height = `${height}px`;
      bar.classList.toggle("active", val > 0.1);
    });
  }
  draw();
}

// ─── WebSocket Connection ─────────────────────────────────────────────────────
function connectWebSocket() {
  if (state.ws && state.ws.readyState <= 1) return;

  const ws = new WebSocket(window.WS_URL);
  state.ws = ws;
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    state.isConnected = true;
    setStatus("connected", "Connected");
    addTranscript("agent", "Connected to Redline Reveal. Click the mic to begin.");
  };

  ws.onclose = () => {
    state.isConnected = false;
    setStatus("", "Disconnected");
    // Reconnect after 3s
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = () => {
    setStatus("", "Connection error");
  };

  ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      // PCM audio from Gemini → play back
      playAudioChunk(event.data);
    } else {
      try {
        const msg = JSON.parse(event.data);
        handleServerMessage(msg);
      } catch (e) {
        console.warn("Non-JSON message:", event.data);
      }
    }
  };
}

function handleServerMessage(msg) {
  switch (msg.type) {
    case "transcript":
      if (msg.text && msg.text.trim()) {
        addTranscript("agent", msg.text);
      }
      break;

    case "map_update":
      if (msg.data) {
        updateChoropleth(msg.data);
        updateStatsFromMapUpdate(msg.data, msg.data.demographic_filter);
        highlightActiveBorough(msg.data);
      }
      break;

    case "error":
      addTranscript("agent", `⚠️ Error: ${msg.message}`);
      setStatus("", "Error");
      break;

    case "pong":
      break;
  }
}

function highlightActiveBorough(data) {
  // Flash-highlight borough with most denials
  const boroughData = data.borough_data || {};
  let maxRate = 0, maxBorough = null;
  for (const [b, stats] of Object.entries(boroughData)) {
    if ((stats.denial_rate_pct || 0) > maxRate) {
      maxRate = stats.denial_rate_pct;
      maxBorough = b;
    }
  }
  if (maxBorough && state.mapPolygons[maxBorough]) {
    const poly = state.mapPolygons[maxBorough];
    let origWeight = 1.5;
    poly.setOptions({ strokeWeight: 3, strokeColor: "#e63946" });
    setTimeout(() => poly.setOptions({ strokeWeight: origWeight, strokeColor: "#30363d" }), 2000);
  }
}

// ─── Audio Playback ───────────────────────────────────────────────────────────
const audioQueue = [];
let isPlaying = false;

async function playAudioChunk(buffer) {
  if (!state.audioContext) {
    state.audioContext = new AudioContext({ sampleRate: 24000 });
  }
  audioQueue.push(buffer);
  if (!isPlaying) drainAudioQueue();
}

async function drainAudioQueue() {
  if (audioQueue.length === 0) { isPlaying = false; return; }
  isPlaying = true;
  const buffer = audioQueue.shift();

  try {
    const ctx = state.audioContext;
    // PCM 16-bit → Float32
    const pcm = new Int16Array(buffer);
    const float = new Float32Array(pcm.length);
    for (let i = 0; i < pcm.length; i++) float[i] = pcm[i] / 32768;

    const audioBuffer = ctx.createBuffer(1, float.length, 24000);
    audioBuffer.copyToChannel(float, 0);
    const src = ctx.createBufferSource();
    src.buffer = audioBuffer;
    src.connect(ctx.destination);
    src.onended = drainAudioQueue;
    src.start();
  } catch (e) {
    console.error("Audio playback error:", e);
    drainAudioQueue();
  }
}

// ─── Microphone Capture ───────────────────────────────────────────────────────
async function startListening() {
  if (state.isListening) { stopListening(); return; }

  // Ensure WebSocket connected
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
    connectWebSocket();
    await new Promise(r => setTimeout(r, 1000));
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    state.audioStream = stream;

    // Analyser for visualizer
    const actx = new AudioContext({ sampleRate: 16000 });
    const analyser = actx.createAnalyser();
    analyser.fftSize = 128;
    const source = actx.createMediaStreamSource(stream);
    source.connect(analyser);
    state.analyser = analyser;

    // ScriptProcessor to get raw PCM
    const processor = actx.createScriptProcessor(4096, 1, 1);
    source.connect(processor);
    processor.connect(actx.destination);

    processor.onaudioprocess = (e) => {
      if (!state.isListening || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;
      const float32 = e.inputBuffer.getChannelData(0);
      // Convert Float32 → Int16 PCM
      const int16 = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      state.ws.send(int16.buffer);
    };

    state.mediaRecorder = processor;
    state.audioContext = actx;
    state.isListening = true;

    document.getElementById("mic-btn").classList.add("listening");
    document.getElementById("mic-label").textContent = "Listening... (click to stop)";
    setStatus("listening", "Listening");
    animateVisualizer(true);

  } catch (err) {
    console.error("Microphone error:", err);
    addTranscript("agent", "⚠️ Could not access microphone. Please check permissions.");
  }
}

function stopListening() {
  state.isListening = false;

  if (state.audioStream) {
    state.audioStream.getTracks().forEach(t => t.stop());
    state.audioStream = null;
  }

  // Signal end of speech to agent
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ type: "end_of_speech" }));
  }

  document.getElementById("mic-btn").classList.remove("listening");
  document.getElementById("mic-btn").classList.add("processing");
  document.getElementById("mic-label").textContent = "Processing...";
  setStatus("processing", "Processing");
  animateVisualizer(false);

  // After agent responds, reset UI
  setTimeout(() => {
    document.getElementById("mic-btn").classList.remove("processing");
    document.getElementById("mic-label").textContent = "Click to Speak";
    if (state.isConnected) setStatus("connected", "Connected");
  }, 3000);
}

// ─── Example Chip Clicks ──────────────────────────────────────────────────────
function sendTextQuery(query) {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
    connectWebSocket();
    setTimeout(() => sendTextQuery(query), 1200);
    return;
  }
  addTranscript("user", query);
  state.ws.send(JSON.stringify({ type: "text_query", query }));
  setStatus("processing", "Processing");
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupVisualizer();

  document.getElementById("mic-btn").addEventListener("click", startListening);

  document.querySelectorAll(".example-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const query = chip.dataset.query;
      // Determine race from query
      let race = null;
      if (/latino|hispanic/i.test(query)) race = "Hispanic";
      else if (/black/i.test(query)) race = "Black";
      else if (/asian/i.test(query)) race = "Asian";
      else if (/white/i.test(query)) race = "White";

      addTranscript("user", query);

      if (race) {
        document.getElementById("map-filter-display").textContent = `${race} applicants`;
        loadMapData(race);
      } else {
        loadMapData(null);
      }

      // Fetch borough stats if borough mentioned
      let borough = null;
      if (/queens|jackson heights/i.test(query)) borough = "Queens";
      else if (/brooklyn/i.test(query)) borough = "Brooklyn";
      else if (/manhattan/i.test(query)) borough = "Manhattan";
      else if (/bronx/i.test(query)) borough = "Bronx";
      else if (/staten island/i.test(query)) borough = "Staten Island";

      if (borough && race) {
        fetch(`${window.BACKEND_URL}/borough/${encodeURIComponent(borough)}?race=${encodeURIComponent(race)}`)
          .then(r => r.json())
          .then(data => {
            if (data.denial_rate_pct !== null) {
              addTranscript("agent",
                `📊 In ${borough}, ${race} applicants faced a ${data.denial_rate_pct}% denial rate in 2022 ` +
                `(${data.denied?.toLocaleString()} denied out of ${data.total?.toLocaleString()} total applications). ` +
                `Connect the voice agent for full narrative analysis.`
              );
              updateStats(
                `${race} (${borough})`,
                data.denial_rate_pct,
                null,
                data.total
              );
              // Also get white rate for comparison
              fetch(`${window.BACKEND_URL}/borough/${encodeURIComponent(borough)}?race=White`)
                .then(r => r.json())
                .then(wd => updateStats(
                  `${race} (${borough})`,
                  data.denial_rate_pct,
                  wd.denial_rate_pct,
                  data.total
                ));
            }
          })
          .catch(console.error);
      } else {
        fetch(`${window.BACKEND_URL}/summary`)
          .then(r => r.json())
          .then(data => {
            const lines = Object.entries(data.borough_summaries || {})
              .filter(([, s]) => s.denial_rate_pct !== null)
              .map(([b, s]) => `${b}: ${s.denial_rate_pct}%`)
              .join(" · ");
            addTranscript("agent", `📊 NYC Borough Denial Rates (2022): ${lines}`);
          })
          .catch(console.error);
      }
    });
  });

  // Connect WebSocket
  connectWebSocket();

  // Ping keepalive
  setInterval(() => {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify({ type: "ping" }));
    }
  }, 25000);
});

// ─── Google Maps Dark Style ───────────────────────────────────────────────────
function darkMapStyles() {
  return [
    { elementType: "geometry", stylers: [{ color: "#0d1117" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#0d1117" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#8b949e" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#0a0f1a" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#161b22" }] },
    { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#21262d" }] },
    { featureType: "poi", stylers: [{ visibility: "off" }] },
    { featureType: "transit", stylers: [{ visibility: "off" }] },
    { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#8b949e" }] },
    { featureType: "administrative.neighborhood", elementType: "labels.text.fill", stylers: [{ color: "#30363d" }] },
    { featureType: "landscape.natural", elementType: "geometry", stylers: [{ color: "#0d1117" }] },
  ];
}
